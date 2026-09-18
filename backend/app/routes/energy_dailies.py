from datetime import date
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.energy_daily import EnergyDaily
from app.models.workshop import Workshop
from app.serializers import energy_daily_json
from app.utils import error, normalize_date

bp = Blueprint("energy_dailies", __name__, url_prefix="/api/energy-dailies")


def _validate(body: dict) -> tuple[str | None, date | None, Decimal | None, Decimal | None]:
    workshop_id = int(body.get("workshopId") or 0)
    if workshop_id <= 0:
        return "请选择车间", None, None, None

    db = SessionLocal()
    try:
        if not db.get(Workshop, workshop_id):
            return "车间不存在", None, None, None
    finally:
        db.close()

    try:
        work_date = normalize_date(str(body.get("workDate", "")))
    except ValueError:
        return "日期格式无效，应为 YYYY-MM-DD", None, None, None

    try:
        kwh = Decimal(str(body.get("kwh", ""))).quantize(Decimal("0.01"))
    except Exception:
        return "用电量(kWh)必须为数字", None, None, None
    if kwh < 0:
        return "用电量(kWh)不能为负", None, None, None

    peak_raw = body.get("peakKw")
    peak_kw = None
    if peak_raw is not None and str(peak_raw).strip() != "":
        try:
            peak_kw = Decimal(str(peak_raw)).quantize(Decimal("0.01"))
        except Exception:
            return "峰值功率(kW)必须为数字", None, None, None
        if peak_kw < 0:
            return "峰值功率(kW)不能为负", None, None, None

    return None, work_date, kwh, peak_kw


def _query_filters():
    workshop_id = request.args.get("workshopId", type=int)
    start_date = None
    end_date = None
    if request.args.get("startDate"):
        try:
            start_date = normalize_date(request.args["startDate"])
        except ValueError:
            start_date = None
    if request.args.get("endDate"):
        try:
            end_date = normalize_date(request.args["endDate"])
        except ValueError:
            end_date = None
    return workshop_id, start_date, end_date


@bp.get("")
@jwt_required()
def list_dailies():
    workshop_id, start_date, end_date = _query_filters()

    db = SessionLocal()
    try:
        q = db.query(EnergyDaily)
        if workshop_id:
            q = q.filter(EnergyDaily.workshop_id == workshop_id)
        if start_date:
            q = q.filter(EnergyDaily.work_date >= start_date)
        if end_date:
            q = q.filter(EnergyDaily.work_date <= end_date)
        rows = q.order_by(EnergyDaily.work_date.desc(), EnergyDaily.id.desc()).all()
        return jsonify([energy_daily_json(r) for r in rows])
    finally:
        db.close()


@bp.get("/summary")
@jwt_required()
def summary():
    workshop_id, start_date, end_date = _query_filters()

    db = SessionLocal()
    try:
        q = select(
            func.coalesce(func.sum(EnergyDaily.kwh), 0),
            func.coalesce(func.max(EnergyDaily.peak_kw), None),
            func.count(EnergyDaily.id),
        )
        if workshop_id:
            q = q.where(EnergyDaily.workshop_id == workshop_id)
        if start_date:
            q = q.where(EnergyDaily.work_date >= start_date)
        if end_date:
            q = q.where(EnergyDaily.work_date <= end_date)

        total_kwh, peak_max, day_count = db.execute(q).one()

        return jsonify(
            {
                "workshopId": workshop_id,
                "startDate": start_date.isoformat() if start_date else None,
                "endDate": end_date.isoformat() if end_date else None,
                "totalKwh": float(total_kwh or 0),
                "maxPeakKw": float(peak_max) if peak_max is not None else None,
                "dayCount": int(day_count or 0),
            }
        )
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_daily():
    body = request.get_json(silent=True) or {}
    err, work_date, kwh, peak_kw = _validate(body)
    if err:
        return error(err, 400)

    db = SessionLocal()
    try:
        row = EnergyDaily(
            workshop_id=int(body["workshopId"]),
            work_date=work_date,
            kwh=kwh,
            peak_kw=peak_kw,
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return error("该车间当天已存在能耗日报", 400)
        db.refresh(row)
        return jsonify(energy_daily_json(row)), 201
    finally:
        db.close()


@bp.put("/<int:item_id>")
@jwt_required()
def update_daily(item_id: int):
    body = request.get_json(silent=True) or {}
    err, work_date, kwh, peak_kw = _validate(body)
    if err:
        return error(err, 400)

    db = SessionLocal()
    try:
        row = db.get(EnergyDaily, item_id)
        if not row:
            return error("能耗日报不存在", 404)

        row.workshop_id = int(body["workshopId"])
        row.work_date = work_date
        row.kwh = kwh
        row.peak_kw = peak_kw
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return error("该车间当天已存在能耗日报", 400)
        db.refresh(row)
        return jsonify(energy_daily_json(row))
    finally:
        db.close()


@bp.delete("/<int:item_id>")
@jwt_required()
def delete_daily(item_id: int):
    db = SessionLocal()
    try:
        row = db.get(EnergyDaily, item_id)
        if not row:
            return error("能耗日报不存在", 404)
        db.delete(row)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
