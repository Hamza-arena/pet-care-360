from datetime import datetime, timedelta

from app.models.appointments import Appointment


def check_appointment_conflict(
    doctor_id,
    appointment_date,
    appointment_time,
    duration_minutes=30,
    room_id=None,
    exclude_appointment_id=None,
):
    """Check if the requested time slot conflicts with an existing appointment for the doctor or room.

    Returns an error message string if there is a conflict, or None if the slot is free.
    """
    new_start = datetime.combine(appointment_date, appointment_time)
    new_end = new_start + timedelta(minutes=duration_minutes or 30)

    # Query active appointments on that date that are not cancelled
    existing_appointments = (
        Appointment.query_active()
        .filter(
            Appointment.appointment_date == appointment_date,
            Appointment.status.notin_(['Cancelled', 'No-Show']),
        )
        .all()
    )

    for apt in existing_appointments:
        if exclude_appointment_id and apt.id == exclude_appointment_id:
            continue

        apt_duration = (
            apt.appointment_type.duration_minutes
            if apt.appointment_type and apt.appointment_type.duration_minutes
            else 30
        )
        apt_start = datetime.combine(apt.appointment_date, apt.appointment_time)
        apt_end = apt_start + timedelta(minutes=apt_duration)

        # Overlap check: new_start < existing_end and new_end > existing_start
        if new_start < apt_end and new_end > apt_start:
            if apt.doctor_id == doctor_id:
                return (
                    f"Doctor schedule conflict: Dr. {apt.doctor.first_name if apt.doctor else ''} "
                    f"is already booked from {apt_start.strftime('%H:%M')} to {apt_end.strftime('%H:%M')}."
                )
            if room_id and apt.room_id and apt.room_id == room_id:
                return (
                    f"Room schedule conflict: Selected room is already occupied from "
                    f"{apt_start.strftime('%H:%M')} to {apt_end.strftime('%H:%M')}."
                )

    return None

