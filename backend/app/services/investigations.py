from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import tools
from app.analytics.dashboard import normalized_timestamp
from app.models import Alert, Merchant, Payment
from app.schemas.investigations import InvestigationItem, InvestigationMetric

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SOURCE_ORDER = {"demo": 0, "razorpay": 1}


def _metric(label: str, value: int | float, format: str) -> InvestigationMetric:
    return InvestigationMetric(label=label, value=value, format=format)


def _fallback_severity(financial_impact: int, *, failure_rate: float | None = None, failures: int = 0) -> str:
    """Small, explainable priority rule used only when no matching alert exists."""
    if financial_impact >= 1_000_000 or (failure_rate is not None and failure_rate >= 50 and failures >= 3):
        return "high"
    if financial_impact > 0 or failures > 0:
        return "medium"
    return "low"


def _open_alerts(session: Session, source: str) -> dict[str, Alert]:
    rows = session.scalars(
        select(Alert)
        .join(Merchant, Alert.merchant_id == Merchant.id)
        .where(Merchant.source == source, Alert.status == "open")
        .order_by(Alert.created_at.desc(), Alert.id)
    ).all()
    latest_by_type: dict[str, Alert] = {}
    for alert in rows:
        latest_by_type.setdefault(alert.type, alert)
    return latest_by_type


def _failure_item(session: Session, source: str, alerts: dict[str, Alert]) -> InvestigationItem | None:
    latest = session.scalar(
        select(func.max(Payment.created_at))
        .select_from(Payment)
        .join(Merchant, Payment.merchant_id == Merchant.id)
        .where(Merchant.source == source)
    )
    if latest is None:
        return None

    end = normalized_timestamp(latest) + timedelta(seconds=1)
    start = end - timedelta(days=1)
    methods = session.execute(
        select(Payment.method, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
        .select_from(Payment)
        .join(Merchant, Payment.merchant_id == Merchant.id)
        .where(
            Merchant.source == source,
            Payment.status == "failed",
            Payment.created_at >= start,
            Payment.created_at < end,
        )
        .group_by(Payment.method)
        .order_by(func.count(Payment.id).desc(), func.sum(Payment.amount).desc(), Payment.method)
    ).first()
    if methods is None:
        return None

    method = str(methods[0])
    stats = tools.payment_failure_stats(session, source, method, "1D", start=start, end=end)
    previous = tools.payment_failure_stats(
        session,
        source,
        method,
        "1D",
        start=start - timedelta(days=1),
        end=start,
    )
    change = round(stats["failure_rate"] - previous["failure_rate"], 1)
    reasons = tools.failure_reason_breakdown(session, source, method, "1D", start=start, end=end)["reasons"]
    dominant_reason = reasons[0]["error_code"] if reasons else "UNKNOWN"
    matching_alert = alerts.get("payment_failure_spike")
    severity = matching_alert.severity if matching_alert else _fallback_severity(
        stats["affected_amount"], failure_rate=stats["failure_rate"], failures=stats["failed_attempts"]
    )
    method_label = method.upper() if method == "upi" else method.title()
    question_method = method.upper() if method == "upi" else method
    evidence = [f"Dominant reason: {dominant_reason}"]
    if previous["total_attempts"]:
        evidence.append(f"Previous comparable window: {previous['failed_attempts']} failed / {previous['total_attempts']} attempts")
    else:
        evidence.append("No attempts in the previous comparable window")

    return InvestigationItem(
        id=f"payment-failure:{source}:{method}",
        type="payment_failure_spike",
        title=f"{method_label} failure spike",
        severity=severity,
        source=source,
        summary=f"{stats['failed_attempts']} failed / {stats['total_attempts']} attempts in the latest activity window.",
        metrics=[
            _metric("Failure rate", stats["failure_rate"], "percent"),
            _metric("Affected", stats["affected_amount"], "money"),
            _metric("Vs previous", change, "percentage_points"),
        ],
        evidence=evidence,
        financial_impact=stats["affected_amount"],
        suggested_question=f"Why are {question_method} payments failing around the latest activity?",
    )


def _settlement_items(session: Session, source: str, alerts: dict[str, Alert]) -> list[InvestigationItem]:
    result = tools.settlement_variance(session, source, None)
    variances = [item for item in result["settlements"] if item["difference"] != 0]
    matching_alert = alerts.get("settlement_discrepancy")
    items = []
    for index, settlement in enumerate(variances):
        impact = abs(settlement["difference"])
        explained = settlement["actual_amount"] == (
            settlement["expected_amount"] - settlement["fees"] + settlement["adjustments"]
        )
        severity = matching_alert.severity if matching_alert and index == 0 else _fallback_severity(impact)
        direction = "lower" if settlement["difference"] < 0 else "higher"
        items.append(InvestigationItem(
            id=f"settlement-variance:{source}:{settlement['settlement_id']}",
            type="settlement_variance",
            title="Settlement variance",
            severity=severity,
            source=source,
            summary=f"Settlement {settlement['settlement_id']} is {direction} than expected.",
            metrics=[
                _metric("Expected", settlement["expected_amount"], "money"),
                _metric("Actual", settlement["actual_amount"], "money"),
                _metric("Difference", settlement["difference"], "money"),
            ],
            evidence=[
                "Recorded fees and adjustments explain the difference" if explained else "Cause is not fully evidenced by recorded fees and adjustments",
                f"Settlement status: {settlement['status']}",
            ],
            financial_impact=impact,
            suggested_question=f"Why is settlement {settlement['settlement_id']} {direction} than expected?",
        ))
    return items


def _reconciliation_items(session: Session, source: str) -> list[InvestigationItem]:
    result = tools.reconciliation_issues(session, source, None, 10)
    items = []
    for index, issue in enumerate(result["issues"]):
        if issue["status"] not in {"open", "investigating"}:
            continue
        impact = int(issue["amount"] or 0)
        entity = issue["payment_id"] or issue["order_id"] or str(index + 1)
        label = issue["issue_type"].replace("_", " ")
        question_subject = f"payment {issue['payment_id']}" if issue["payment_id"] else f"order {issue['order_id']}" if issue["order_id"] else "this issue"
        items.append(InvestigationItem(
            id=f"reconciliation:{source}:{issue['issue_type']}:{entity}",
            type="reconciliation_issue",
            title=label.title(),
            severity=_fallback_severity(impact),
            source=source,
            summary=issue["description"],
            metrics=[_metric("Exposure", impact, "money")] if impact else [],
            evidence=[f"Status: {issue['status']}", f"Exception type: {issue['issue_type']}"],
            financial_impact=impact,
            suggested_question=f"Investigate the {label} for {question_subject}.",
        ))
    return items


def _unrepresented_alert_items(source: str, alerts: dict[str, Alert]) -> list[InvestigationItem]:
    represented = {"payment_failure_spike", "settlement_discrepancy"}
    items = []
    for alert_type, alert in alerts.items():
        if alert_type in represented:
            continue
        impact = int(alert.metric_value or 0) if alert_type.endswith(("discrepancy", "amount")) else 0
        metrics = []
        if alert.metric_value is not None:
            metrics.append(_metric("Current", alert.metric_value, "count"))
        if alert.baseline_value is not None:
            metrics.append(_metric("Baseline", alert.baseline_value, "count"))
        items.append(InvestigationItem(
            id=f"alert:{source}:{alert_type}:{alert.id}",
            type="alert",
            title=alert.title,
            severity=alert.severity,
            source=source,
            summary=alert.description,
            metrics=metrics,
            evidence=[f"Recorded open alert: {alert.type}"],
            financial_impact=impact,
            suggested_question=f"What evidence supports the {alert.title.lower()} alert?",
        ))
    return items


def get_investigations(session: Session, source: str = "all") -> list[InvestigationItem]:
    sources = [source] if source != "all" else ["demo", "razorpay"]
    items: list[InvestigationItem] = []
    for scoped_source in sources:
        alerts = _open_alerts(session, scoped_source)
        source_items: list[InvestigationItem] = []
        failure = _failure_item(session, scoped_source, alerts)
        if failure:
            source_items.append(failure)
        source_items.extend(_settlement_items(session, scoped_source, alerts))
        source_items.extend(_reconciliation_items(session, scoped_source))
        source_items.extend(_unrepresented_alert_items(scoped_source, alerts))
        items.extend(sorted(
            source_items,
            key=lambda item: (SEVERITY_ORDER[item.severity], -item.financial_impact, item.type, item.id),
        )[:4])

    return sorted(
        items,
        key=lambda item: (
            SEVERITY_ORDER[item.severity],
            -item.financial_impact,
            SOURCE_ORDER[item.source],
            item.type,
            item.id,
        ),
    )
