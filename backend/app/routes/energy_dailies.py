from decimal import Decimal
from math import isfinite

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


def _validate(body: dict) -> str | None:
    workshop_id = int(body.get("workshopId") or 0)
    if workshop_id <= 0:
        return "请选择所属车间"

    db = SessionLocal()
    try:
        if not db.get(Workshop, workshop_id):
            return "所属车间不存在"
    finally:
        db.close()

    if normalize_date(str(body.get("workDate", ""))) is None:
        return "日期不能为空，格式 YYYY-MM-DD"

    kwh_raw = body.get("kwh")
    if kwh_raw is None or str(kwh_raw).strip() == "":
        return "用电量(kWh)不能为空"
    try:
        kwh = float(kwh_raw)
    except (TypeError, ValueError):
        return "用电量(kWh)必须是非负数字"
    if not isfinite(kwh) or kwh < 0:
        return "用电量(kWh)不能为负数"

    peak_raw = body.get("peakKw")
    if peak_raw is not None and str(peak_raw).strip() != "":
        try:
            peak = float(peak_raw)
        except (TypeError, ValueError):
            return "峰值功率(kW)必须是非负数字"
        if not isfinite(peak) or peak < 0:
            return "峰值功率(kW)不能为负数"

    return None


def _apply_filters(query, args):
    workshop_id = args.get("workshopId", type=int)
    if workshop_id:
        query = query.where(EnergyDaily.workshop_id == workshop_id)
    start = normalize_date(args.get("start", ""))
    if start:
        query = query.where(EnergyDaily.work_date >= start)
    end = normalize_date(args.get("end", ""))
    if end:
        query = query.where(EnergyDaily.work_date <= end)
    return query, workshop_id, start, end


@bp.get("")
@jwt_required()
def list_energy_dailies():
    db = SessionLocal()
    try:
        query = select(EnergyDaily)
        query, _wid, _start, _end = _apply_filters(query, request.args)
        rows = db.scalars(
            query.order_by(EnergyDaily.work_date.desc(), EnergyDaily.id.desc())
        ).all()
        return jsonify([energy_daily_json(r) for r in rows])
    finally:
        db.close()


@bp.get("/summary")
@jwt_required()
def summary_energy_dailies():
    db = SessionLocal()
    try:
        query = select(
            func.coalesce(func.sum(EnergyDaily.kwh), 0),
            func.count(EnergyDaily.id),
        )
        query, workshop_id, start, end = _apply_filters(query, request.args)
        total_kwh, days = db.execute(query).one()
        return jsonify(
            {
                "workshopId": workshop_id,
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
                "days": days,
                "totalKwh": float(total_kwh or 0),
            }
        )
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_energy_daily():
    body = request.get_json(silent=True) or {}
    err = _validate(body)
    if err:
        return error(err, 400)

    peak_raw = body.get("peakKw")
    db = SessionLocal()
    try:
        row = EnergyDaily(
            workshop_id=int(body["workshopId"]),
            work_date=normalize_date(str(body["workDate"])),
            kwh=Decimal(str(body["kwh"])),
            peak_kw=(
                Decimal(str(peak_raw))
                if peak_raw is not None and str(peak_raw).strip() != ""
                else None
            ),
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return error("该车间该日期已存在能耗日报", 400)
        db.refresh(row)
        return jsonify(energy_daily_json(row)), 201
    finally:
        db.close()


@bp.put("/<int:item_id>")
@jwt_required()
def update_energy_daily(item_id: int):
    body = request.get_json(silent=True) or {}
    err = _validate(body)
    if err:
        return error(err, 400)

    peak_raw = body.get("peakKw")
    db = SessionLocal()
    try:
        row = db.get(EnergyDaily, item_id)
        if not row:
            return error("能耗日报不存在", 404)

        row.workshop_id = int(body["workshopId"])
        row.work_date = normalize_date(str(body["workDate"]))
        row.kwh = Decimal(str(body["kwh"]))
        row.peak_kw = (
            Decimal(str(peak_raw))
            if peak_raw is not None and str(peak_raw).strip() != ""
            else None
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return error("该车间该日期已存在能耗日报", 400)
        db.refresh(row)
        return jsonify(energy_daily_json(row))
    finally:
        db.close()


@bp.delete("/<int:item_id>")
@jwt_required()
def delete_energy_daily(item_id: int):
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
