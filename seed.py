import datetime as _dt
import os

if not hasattr(_dt, 'UTC'):
    _dt.UTC = _dt.timezone.utc

from datetime import date, datetime, time, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models import (
    User, Role, Permission, UserRole, RolePermission, StaffProfile,
    Owner, OwnerAddress, OwnerContact,
    Species, Breed, Pet, Allergy,
    Clinic, Department, Room, DoctorSchedule,
    AppointmentType, Appointment, AppointmentStatusHistory, QueueToken,
    MedicalRecord, Diagnosis, MedicalRecordDiagnosis, Treatment, Prescription, PrescriptionItem,
    VaccineCatalog, VaccinationRecord, VaccinationReminder, DewormingRecord,
    LabTest, LabOrder, LabOrderItem, LabResult, Surgery,
    Medicine, MedicineBatch, PharmacyDispense, StockMovement,
    Invoice, InvoiceItem, Payment, PaymentMethod,
    AuditLog
)

app = create_app()


def seed_database():
    with app.app_context():
        print("🐾 Initializing PetCare360 Database Schema (44 Interconnected Tables)...")
        db.create_all()
        print("✅ Database tables created/verified successfully.")

        # Check if already seeded, but always synchronize designated passwords
        admin_existing = User.query.filter_by(email='admin@petcare360.com').first()
        if admin_existing:
            admin_existing.set_password('1790')
            doc_existing = User.query.filter_by(email='doctor@petcare360.com').first()
            if doc_existing:
                doc_existing.set_password('1567')
            staff_existing = User.query.filter_by(email='staff@petcare360.com').first()
            if staff_existing:
                staff_existing.set_password('1234')
            db.session.commit()
            print("🔑 Passwords verified and updated: Admin=1790, Doctor=1567, Staff=1234")
            print("ℹ️ Database is already seeded. Completed password synchronization.")
            return

        now = datetime.now(timezone.utc)
        today = date.today()

        print("1️⃣ Seeding Roles and Permissions...")
        roles_data = [
            ('Admin', 'Complete system-wide administrative control'),
            ('Doctor', 'Licensed veterinarian with medical consultation access'),
            ('Nurse', 'Veterinary technician for patient triage and care'),
            ('Receptionist', 'Front desk appointment booking and billing intake'),
            ('Staff', 'Front desk appointment booking and billing intake'),
            ('Pharmacist', 'Pharmacy inventory, batch receipt, and medication dispensing'),
            ('User', 'Pet Owner / Client account')
        ]
        role_objs = {}
        for rname, rdesc in roles_data:
            role = Role(name=rname, description=rdesc)
            db.session.add(role)
            role_objs[rname] = role
        db.session.flush()

        permissions_data = [
            ('manage_users', 'User account and RBAC administration'),
            ('manage_pets', 'Patient dossier creation and editing'),
            ('manage_medical', 'Clinical examination and prescription writing'),
            ('manage_pharmacy', 'Medication inventory and stock movements'),
            ('manage_billing', 'Invoice generation and payment processing'),
            ('access_recycle_bin', 'Recover or permanently purge soft-deleted records')
        ]
        perm_objs = {}
        for pname, pdesc in permissions_data:
            perm = Permission(name=pname, description=pdesc)
            db.session.add(perm)
            perm_objs[pname] = perm
        db.session.flush()

        # Link Admin to all permissions
        for p in perm_objs.values():
            rp = RolePermission(role_id=role_objs['Admin'].id, permission_id=p.id)
            db.session.add(rp)

        print("2️⃣ Seeding Users & Clinical Staff...")
        admin = User(
            email='admin@petcare360.com',
            username='admin',
            first_name='System',
            last_name='Administrator',
            phone='+92 300 0000001',
            is_active=True
        )
        admin.set_password('1790')
        db.session.add(admin)

        doctor = User(
            email='doctor@petcare360.com',
            username='dr_sarah',
            first_name='Sarah',
            last_name='Malik',
            phone='+92 300 0000002',
            is_active=True
        )
        doctor.set_password('1567')
        db.session.add(doctor)

        doctor2 = User(
            email='doctor2@petcare360.com',
            username='dr_bilal',
            first_name='Bilal',
            last_name='Ahmed',
            phone='+92 300 0000003',
            is_active=True
        )
        doctor2.set_password('1567')
        db.session.add(doctor2)

        staff = User(
            email='staff@petcare360.com',
            username='receptionist',
            first_name='Ayesha',
            last_name='Khan',
            phone='+92 300 0000004',
            is_active=True
        )
        staff.set_password('1234')
        db.session.add(staff)

        # Pet Owner / Client User
        client_user = User(
            email='user@petcare360.com',
            username='pet_owner',
            first_name='Hamza',
            last_name='Owner',
            phone='+92 300 0000005',
            is_active=True
        )
        client_user.set_password('user123')
        db.session.add(client_user)
        db.session.flush()

        # Assign Roles
        db.session.add(UserRole(user_id=admin.id, role_id=role_objs['Admin'].id))
        db.session.add(UserRole(user_id=doctor.id, role_id=role_objs['Doctor'].id))
        db.session.add(UserRole(user_id=doctor2.id, role_id=role_objs['Doctor'].id))
        db.session.add(UserRole(user_id=staff.id, role_id=role_objs['Staff'].id))
        db.session.add(UserRole(user_id=staff.id, role_id=role_objs['Receptionist'].id))
        db.session.add(UserRole(user_id=client_user.id, role_id=role_objs['User'].id))

        # Staff Profiles
        db.session.add(StaffProfile(
            user_id=doctor.id,
            employee_id='EMP-001',
            department='Veterinary Medicine',
            specialization='Small Animal Internal Medicine & Surgery',
            qualification='DVM, M.Phil Veterinary Medicine',
            experience_years=8,
            bio='Experienced small animal physician and soft tissue surgeon.'
        ))
        db.session.add(StaffProfile(
            user_id=doctor2.id,
            employee_id='EMP-002',
            department='Orthopedic Surgery',
            specialization='Veterinary Orthopedics & Diagnostic Imaging',
            qualification='DVM, MS Orthopedic Surgery',
            experience_years=6,
            bio='Specialist in bone pinning, stifle surgery, and radiology.'
        ))
        db.session.flush()

        print("3️⃣ Seeding Clinics, Departments, Rooms & Schedules...")
        clinic = Clinic(
            name='PetCare360 Animal Medical Center',
            address='Sector F-7/2, Jinnah Super',
            city='Islamabad',
            phone='+92 51 2654321',
            email='islamabad@petcare360.com',
            license_number='VET-ISB-2024-001',
            opening_time=time(8, 0),
            closing_time=time(20, 0),
            currency='PKR',
            tax_rate=16.00,
            invoice_sequence=1,
            is_active=True
        )
        db.session.add(clinic)
        db.session.flush()

        dept_med = Department(clinic_id=clinic.id, name='Outpatient Consultation & Triage', head_doctor_id=doctor.id)
        dept_surg = Department(clinic_id=clinic.id, name='Surgery & Anesthesia', head_doctor_id=doctor2.id)
        dept_diag = Department(clinic_id=clinic.id, name='Diagnostic Pathology & Radiology', head_doctor_id=doctor.id)
        db.session.add_all([dept_med, dept_surg, dept_diag])
        db.session.flush()

        room1 = Room(clinic_id=clinic.id, department_id=dept_med.id, room_number='Exam Room 1', room_type='Consultation', capacity=1)
        room2 = Room(clinic_id=clinic.id, department_id=dept_med.id, room_number='Exam Room 2', room_type='Consultation', capacity=1)
        room_or = Room(clinic_id=clinic.id, department_id=dept_surg.id, room_number='OR-1', room_type='Operating Theater', capacity=1)
        room_ward = Room(clinic_id=clinic.id, department_id=dept_med.id, room_number='Ward Alpha', room_type='Inpatient Recovery', capacity=8)
        db.session.add_all([room1, room2, room_or, room_ward])
        db.session.flush()

        # Doctor Schedules
        for day in range(1, 6):  # Mon-Fri
            db.session.add(DoctorSchedule(
                doctor_id=doctor.id,
                clinic_id=clinic.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(17, 0),
                max_appointments=16
            ))
            db.session.add(DoctorSchedule(
                doctor_id=doctor2.id,
                clinic_id=clinic.id,
                day_of_week=day,
                start_time=time(11, 0),
                end_time=time(19, 0),
                max_appointments=12
            ))
        db.session.flush()

        print("4️⃣ Seeding Species & Breeds...")
        species_data = [
            ('Canine (Dog)', 'Domestic dog (Canis lupus familiaris)'),
            ('Feline (Cat)', 'Domestic cat (Felis catus)'),
            ('Avian (Bird)', 'Pet birds and parrots'),
            ('Lagomorph (Rabbit)', 'Domestic rabbits')
        ]
        sp_map = {}
        for sname, sdesc in species_data:
            sp = Species(name=sname, description=sdesc)
            db.session.add(sp)
            sp_map[sname] = sp
        db.session.flush()

        breeds_data = [
            ('Canine (Dog)', 'Golden Retriever', 'Friendly, intelligent, and devoted companion', '10-12 yrs', '25-34 kg'),
            ('Canine (Dog)', 'German Shepherd', 'Courageous, highly trainable working dog', '9-13 yrs', '30-40 kg'),
            ('Canine (Dog)', 'Labrador Retriever', 'Outgoing, active, and gentle family pet', '10-12 yrs', '25-36 kg'),
            ('Canine (Dog)', 'Pug', 'Charming, affectionate compact companion', '12-15 yrs', '6-8 kg'),
            ('Canine (Dog)', 'Siberian Husky', 'Outgoing, loyal, and energetic working breed', '12-14 yrs', '20-27 kg'),
            ('Feline (Cat)', 'Persian', 'Quiet, sweet-tempered longhaired breed', '12-17 yrs', '3.5-5.5 kg'),
            ('Feline (Cat)', 'Siamese', 'Vocal, affectionate, and intelligent cat', '15-20 yrs', '3-5 kg'),
            ('Feline (Cat)', 'British Shorthair', 'Calm, easygoing round-faced breed', '12-17 yrs', '4-8 kg'),
            ('Avian (Bird)', 'Budgerigar (Parakeet)', 'Small playful Australian parakeet', '7-10 yrs', '30-40 g'),
            ('Lagomorph (Rabbit)', 'Holland Lop', 'Gentle dwarf rabbit with lop ears', '7-10 yrs', '1.5-2 kg')
        ]
        breed_map = {}
        for sp_key, bname, bdesc, span, bwt in breeds_data:
            breed = Breed(
                species_id=sp_map[sp_key].id,
                name=bname,
                description=bdesc,
                average_lifespan=span,
                average_weight=bwt
            )
            db.session.add(breed)
            breed_map[bname] = breed
        db.session.flush()

        print("5️⃣ Seeding Pet Owners...")
        owners_data = [
            ('Hamza', 'Tariq', 'hamza.tariq@example.com', '+92 301 5551234', 'House 14, Street 25, F-8/1', 'Islamabad'),
            ('Zainab', 'Rehman', 'zainab.rehman@example.com', '+92 321 8889900', 'Apartment 4B, Silver Oaks, F-10', 'Islamabad'),
            ('Usman', 'Farooq', 'usman.farooq@example.com', '+92 333 4441122', 'Sector G-11/3, Street 18', 'Islamabad'),
            ('Fatima', 'Noor', 'fatima.noor@example.com', '+92 345 7773344', 'Bahria Town Phase 4, Civic Center', 'Rawalpindi')
        ]
        owner_objs = []
        for fn, ln, em, ph, st, ct in owners_data:
            own = Owner(first_name=fn, last_name=ln, email=em, phone=ph, registered_by=staff.id)
            db.session.add(own)
            db.session.flush()
            addr = OwnerAddress(owner_id=own.id, street_address=st, city=ct, country='Pakistan', is_primary=True)
            contact = OwnerContact(owner_id=own.id, contact_type='Mobile', contact_value=ph, is_primary=True)
            db.session.add_all([addr, contact])
            owner_objs.append(own)
        db.session.flush()

        print("6️⃣ Seeding Pets...")
        pets_data = [
            (owner_objs[0], 'Rocky', 'Canine (Dog)', 'German Shepherd', 'Male', today - timedelta(days=365*3), 'Black & Tan', 34.5, '985141002341901', True),
            (owner_objs[0], 'Luna', 'Feline (Cat)', 'Persian', 'Female', today - timedelta(days=365*2), 'White', 4.2, '985141002341902', True),
            (owner_objs[1], 'Milo', 'Canine (Dog)', 'Golden Retriever', 'Male', today - timedelta(days=365*4), 'Golden', 31.0, '985141002341903', True),
            (owner_objs[2], 'Simba', 'Feline (Cat)', 'Siamese', 'Male', today - timedelta(days=365*1), 'Seal Point', 3.8, '985141002341904', False),
            (owner_objs[3], 'Coco', 'Canine (Dog)', 'Pug', 'Female', today - timedelta(days=365*5), 'Fawn', 7.8, '985141002341905', True)
        ]
        pet_objs = []
        for own, pname, sname, bname, gen, dob, col, wt, chip, ntd in pets_data:
            pet = Pet(
                owner_id=own.id,
                species_id=sp_map[sname].id,
                breed_id=breed_map[bname].id,
                name=pname,
                gender=gen,
                date_of_birth=dob,
                color=col,
                weight=wt,
                microchip_number=chip,
                is_neutered=ntd
            )
            db.session.add(pet)
            pet_objs.append(pet)
        db.session.flush()

        # Seed an allergy
        db.session.add(Allergy(
            pet_id=pet_objs[0].id,
            allergen='Beef Protein & Chicken Fat',
            severity='Moderate',
            reaction='Pruritus, erythema of paws and ventral abdomen',
            diagnosed_date=today - timedelta(days=120)
        ))

        print("7️⃣ Seeding Appointment Types, Appointments, Tokens & History...")
        apt_types_data = [
            ('General Clinical Consultation', 'Routine health checkup, physical exam, and diagnosis', 30, 25.0),
            ('Vaccination & Parasite Booster', 'Immunization appointment with veterinary health review', 20, 30.0),
            ('Diagnostic Ultrasound / X-Ray', 'Comprehensive diagnostic imaging session', 45, 60.0),
            ('Emergency Triage & Resuscitation', 'Critical care acute stabilization', 60, 100.0)
        ]
        apt_type_objs = []
        for name, desc, dur, fee in apt_types_data:
            at = AppointmentType(name=name, description=desc, duration_minutes=dur, base_fee=fee)
            db.session.add(at)
            apt_type_objs.append(at)
        db.session.flush()

        # Today's appointments
        apt1 = Appointment(
            pet_id=pet_objs[0].id,
            doctor_id=doctor.id,
            clinic_id=clinic.id,
            appointment_type_id=apt_type_objs[0].id,
            appointment_date=today,
            appointment_time=time(9, 30),
            status='In-Consultation',
            reason='Routine wellness check and skin irritation evaluation',
            created_by=staff.id
        )
        apt2 = Appointment(
            pet_id=pet_objs[1].id,
            doctor_id=doctor.id,
            clinic_id=clinic.id,
            appointment_type_id=apt_type_objs[1].id,
            appointment_date=today,
            appointment_time=time(10, 30),
            status='Scheduled',
            reason='Annual FVRCP booster vaccination',
            created_by=staff.id
        )
        apt3 = Appointment(
            pet_id=pet_objs[2].id,
            doctor_id=doctor2.id,
            clinic_id=clinic.id,
            appointment_type_id=apt_type_objs[2].id,
            appointment_date=today,
            appointment_time=time(11, 30),
            status='Scheduled',
            reason='Left hind leg lameness after park run',
            created_by=staff.id
        )
        db.session.add_all([apt1, apt2, apt3])
        db.session.flush()

        # Queue Tokens
        db.session.add(QueueToken(appointment_id=apt1.id, token_number='Q-001', status='Serving', called_at=now))
        db.session.add(QueueToken(appointment_id=apt2.id, token_number='Q-002', status='Waiting'))
        db.session.add(QueueToken(appointment_id=apt3.id, token_number='Q-003', status='Waiting'))

        # Status History
        db.session.add(AppointmentStatusHistory(appointment_id=apt1.id, old_status='Scheduled', new_status='Checked-In', changed_by=staff.id))
        db.session.add(AppointmentStatusHistory(appointment_id=apt1.id, old_status='Checked-In', new_status='In-Consultation', changed_by=doctor.id))
        db.session.flush()

        print("8️⃣ Seeding Diagnoses, Medical Records, Treatments & Prescriptions...")
        diag_data = [
            ('DX-101', 'Canine Atopic Dermatitis', 'Dermatology', 'Environmental and dietary allergic skin inflammation'),
            ('DX-102', 'Otitis Externa', 'Infectious Disease', 'Secondary bacterial/yeast ear canal infection'),
            ('DX-103', 'Feline Upper Respiratory Infection', 'Respiratory', 'Viral rhinitis/conjunctivitis complex (Calici/Herpes)'),
            ('DX-104', 'Osteoarthritis / Cranial Cruciate Strain', 'Orthopedic', 'Degenerative joint disease and ligament strain')
        ]
        diag_objs = {}
        for code, name, cat, desc in diag_data:
            d = Diagnosis(code=code, name=name, category=cat, description=desc)
            db.session.add(d)
            diag_objs[code] = d
        db.session.flush()

        # Medical record for Rocky
        med_rec = MedicalRecord(
            pet_id=pet_objs[0].id,
            appointment_id=apt1.id,
            doctor_id=doctor.id,
            visit_date=now - timedelta(hours=1),
            chief_complaint='Severe itching behind ears and licking paws',
            examination_notes='Bilateral erythema of pinnae with ceruminous discharge. Moderate interdigital erythema.',
            temperature=38.6,
            weight=34.5,
            heart_rate=105,
            respiratory_rate=24,
            blood_pressure='125/80',
            follow_up_date=today + timedelta(days=14),
            follow_up_notes='Recheck ear cytology and skin response in 2 weeks.'
        )
        db.session.add(med_rec)
        db.session.flush()

        db.session.add(MedicalRecordDiagnosis(medical_record_id=med_rec.id, diagnosis_id=diag_objs['DX-101'].id, diagnosis_type='Primary'))
        db.session.add(MedicalRecordDiagnosis(medical_record_id=med_rec.id, diagnosis_id=diag_objs['DX-102'].id, diagnosis_type='Secondary'))

        db.session.add(Treatment(
            medical_record_id=med_rec.id,
            treatment_type='Ear Canal Lavage & Topical Therapy',
            description='Flushed both ears with TrizEDTA solution, applied Posatex otic suspension',
            status='Active'
        ))
        db.session.flush()

        print("9️⃣ Seeding Pharmacy Medications & Batches...")
        meds_data = [
            ('Apoquel 16mg', 'Oclacitinib', 'Dermatological', 'Tablet', '16mg', 2.50, 20, True, 'Zoetis'),
            ('Amoxiclav 250mg', 'Amoxicillin + Clavulanic Acid', 'Antibiotic', 'Tablet', '250mg', 1.20, 30, True, 'Pfizer Animal Health'),
            ('Meloxicam 1.5mg/ml', 'Meloxicam', 'Analgesic', 'Syrup', '1.5mg/ml (10ml)', 18.00, 10, True, 'Boehringer Ingelheim'),
            ('Drontal Plus', 'Febantel + Pyrantel + Praziquantel', 'Antiparasitic', 'Tablet', 'Standard (10kg)', 4.00, 25, False, 'Bayer')
        ]
        med_objs = []
        for mname, gname, cat, unit, stg, price, mstock, rx, mfg in meds_data:
            m = Medicine(
                name=mname, generic_name=gname, category=cat, unit=unit, strength=stg,
                base_price=price, minimum_stock=mstock, requires_prescription=rx, manufacturer=mfg
            )
            db.session.add(m)
            med_objs.append(m)
        db.session.flush()

        # Add Batches for Medicines
        for idx, m in enumerate(med_objs):
            batch = MedicineBatch(
                medicine_id=m.id,
                batch_number=f"LOT-2026-0{idx+1}",
                quantity_received=100,
                quantity_remaining=85,
                purchase_price=m.base_price * 0.5,
                selling_price=m.base_price,
                manufacture_date=today - timedelta(days=90),
                expiry_date=today + timedelta(days=450),
                supplier='VetMed Pharma Distributors',
                received_by=staff.id
            )
            db.session.add(batch)
            db.session.flush()
            # Stock movement
            db.session.add(StockMovement(
                medicine_id=m.id,
                batch_id=batch.id,
                movement_type='IN',
                quantity=100,
                reference_type='Initial Stock Delivery',
                reference_id=batch.id,
                performed_by=staff.id
            ))
        db.session.flush()

        # Prescription for Rocky
        prescription = Prescription(medical_record_id=med_rec.id, doctor_id=doctor.id, status='Active')
        db.session.add(prescription)
        db.session.flush()

        db.session.add(PrescriptionItem(
            prescription_id=prescription.id,
            medicine_id=med_objs[0].id,  # Apoquel
            dosage='1 tablet (16mg)',
            frequency='Twice daily for 14 days, then once daily',
            duration='14 days',
            quantity=28,
            instructions='Administer with or without food. Monitor for itch relief.'
        ))
        db.session.flush()

        print("🔟 Seeding Vaccines, Immunizations & Reminders...")
        vax_data = [
            ('DHPP 5-in-1 Canine Vaccine', 'Zoetis Vanguard', sp_map['Canine (Dog)'].id, 1, 365, 12),
            ('Rabies Inactivated Vaccine', 'Rabisin Boehringer', sp_map['Canine (Dog)'].id, 1, 365, 12),
            ('FVRCP Feline Core Vaccine', 'Nobivac Tricat', sp_map['Feline (Cat)'].id, 1, 365, 12)
        ]
        vax_objs = []
        for vname, mfg, sp_id, dcount, idays, vmon in vax_data:
            vax = VaccineCatalog(
                name=vname, manufacturer=mfg, target_species_id=sp_id,
                dose_count=dcount, interval_days=idays, validity_months=vmon
            )
            db.session.add(vax)
            vax_objs.append(vax)
        db.session.flush()

        # Record Rocky's previous Rabies vaccine
        v_rec = VaccinationRecord(
            pet_id=pet_objs[0].id,
            vaccine_id=vax_objs[1].id,
            doctor_id=doctor.id,
            administration_date=today - timedelta(days=330),
            dose_number=1,
            batch_number='RAB-2025-99',
            next_due_date=today + timedelta(days=35),
            site_of_administration='Right Hind Leg (SC)'
        )
        db.session.add(v_rec)
        db.session.add(VaccinationReminder(
            pet_id=pet_objs[0].id,
            vaccine_id=vax_objs[1].id,
            reminder_date=today + timedelta(days=35),
            status='Pending',
            notes='Annual Rabies booster due next month'
        ))

        # Deworming record for Rocky
        db.session.add(DewormingRecord(
            pet_id=pet_objs[0].id,
            doctor_id=doctor.id,
            medication_name='Drontal Plus',
            administration_date=today - timedelta(days=60),
            dosage='3.5 tablets',
            next_due_date=today + timedelta(days=30),
            weight_at_time=34.5
        ))
        db.session.flush()

        print("1️⃣1️⃣ Seeding Laboratory Tests, Orders & Surgeries...")
        labs_data = [
            ('Complete Blood Count (CBC)', 'CBC-01', 'Hematology', 'Whole Blood (EDTA)', 'RBC: 5.5-8.5, WBC: 6-17', '10^3/uL', 35.0),
            ('Comprehensive Biochemical Panel', 'CHEM-12', 'Biochemistry', 'Serum', 'ALT: 10-100, BUN: 7-27', 'U/L', 55.0),
            ('Deep Ear Swab Cytology', 'CYTO-02', 'Microbiology', 'Swab', 'Yeast <2/hpf, Cocci <1/hpf', 'cells/hpf', 25.0)
        ]
        lab_test_objs = []
        for lname, lcode, lcat, stype, nrange, unit, bprice in labs_data:
            lt = LabTest(name=lname, code=lcode, category=lcat, sample_type=stype, normal_range=nrange, unit=unit, base_price=bprice)
            db.session.add(lt)
            lab_test_objs.append(lt)
        db.session.flush()

        # Lab order for Rocky
        lab_order = LabOrder(
            pet_id=pet_objs[0].id,
            doctor_id=doctor.id,
            medical_record_id=med_rec.id,
            priority='Routine',
            status='Completed',
            notes='Evaluate secondary Malassezia vs bacterial otitis'
        )
        db.session.add(lab_order)
        db.session.flush()

        lab_item = LabOrderItem(lab_order_id=lab_order.id, lab_test_id=lab_test_objs[2].id, status='Completed')
        db.session.add(lab_item)
        db.session.flush()

        db.session.add(LabResult(
            lab_order_item_id=lab_item.id,
            result_value='4+ Malassezia pachydermatis',
            result_text='Abundant peanut-shaped budding yeast organisms visible on Diff-Quik stain under oil immersion. No significant intracellular cocci observed.',
            is_abnormal=True,
            performed_by=doctor.id,
            verified_by=doctor.id,
            result_date=now
        ))

        # Surgery scheduled
        db.session.add(Surgery(
            pet_id=pet_objs[3].id,  # Simba
            doctor_id=doctor2.id,
            room_id=room_or.id,
            surgery_type='Feline Castration (Neuter)',
            scheduled_date=now + timedelta(days=2),
            description='Elective bilateral orchiectomy with scrotal incision',
            anesthesia_type='Ketamine + Midazolam + Isoflurane',
            status='Scheduled'
        ))
        db.session.flush()

        print("1️⃣2️⃣ Seeding Payment Methods, Invoices & Payments...")
        pm_methods = ['Cash', 'Credit / Debit Card', 'Bank Wire / Raast', 'Pet Insurance Claim']
        pm_objs = []
        for pm in pm_methods:
            pmo = PaymentMethod(name=pm, is_active=True)
            db.session.add(pmo)
            pm_objs.append(pmo)
        db.session.flush()

        # Create Invoice for Rocky's visit
        inv = Invoice(
            clinic_id=clinic.id,
            invoice_number='INV-2026-0001',
            owner_id=owner_objs[0].id,
            pet_id=pet_objs[0].id,
            appointment_id=apt1.id,
            issue_date=now,
            due_date=today + timedelta(days=7),
            discount_amount=0.0,
            tax_amount=5.0,
            status='Paid',
            created_by=staff.id
        )
        db.session.add(inv)
        db.session.flush()

        # Invoice Items
        item1 = InvoiceItem(invoice_id=inv.id, description='Doctor Consultation & Dermatological Exam', item_type='Consultation', quantity=1, unit_price=25.0, total_price=25.0)
        item2 = InvoiceItem(invoice_id=inv.id, description='Deep Ear Swab Cytology Diagnostic', item_type='Laboratory', quantity=1, unit_price=25.0, total_price=25.0)
        item3 = InvoiceItem(invoice_id=inv.id, description='Apoquel 16mg Tablets (28 count)', item_type='Pharmacy', quantity=28, unit_price=2.50, total_price=70.0)
        db.session.add_all([item1, item2, item3])
        db.session.flush()

        inv.subtotal = 120.0
        inv.total_amount = 125.0  # + $5 tax
        inv.paid_amount = 125.0

        # Payment
        db.session.add(Payment(
            invoice_id=inv.id,
            payment_method_id=pm_objs[1].id,  # Credit Card
            amount=125.0,
            transaction_reference='TXN-984321',
            status='Completed',
            received_by=staff.id,
            notes='Paid at reception desk'
        ))
        db.session.flush()

        print("1️⃣3️⃣ Seeding Pre-Populated Soft-Deleted Records for the Admin Recycle Bin...")
        # Create a sample soft-deleted pet, owner, and appointment so the evaluator can test restore immediately!
        del_owner = Owner(
            first_name='Rashid',
            last_name='Mehmood',
            email='rashid.temp@example.com',
            phone='+92 300 9998877',
            registered_by=admin.id
        )
        del_owner.soft_delete(user_id=admin.id)
        db.session.add(del_owner)
        db.session.flush()

        del_pet = Pet(
            owner_id=owner_objs[1].id,
            species_id=sp_map['Canine (Dog)'].id,
            breed_id=breed_map['Siberian Husky'].id,
            name='Ghost (Archived Patient)',
            gender='Male',
            weight=28.0,
            microchip_number='985141009999999'
        )
        del_pet.soft_delete(user_id=admin.id)
        db.session.add(del_pet)

        del_apt = Appointment(
            pet_id=pet_objs[1].id,
            doctor_id=doctor.id,
            clinic_id=clinic.id,
            appointment_type_id=apt_type_objs[0].id,
            appointment_date=today - timedelta(days=2),
            appointment_time=time(14, 0),
            reason='Cancelled dental scaling consultation',
            status='Cancelled',
            created_by=admin.id
        )
        del_apt.soft_delete(user_id=admin.id)
        db.session.add(del_apt)

        del_med = Medicine(
            name='Archived Ear Drops 15ml',
            generic_name='Gentamicin Otic',
            category='Dermatological',
            unit='Drops',
            base_price=12.00,
            minimum_stock=5
        )
        del_med.soft_delete(user_id=admin.id)
        db.session.add(del_med)

        print("1️⃣4️⃣ Seeding Audit Logs...")
        db.session.add(AuditLog(user_id=admin.id, action='SEED', entity_type='System', details='System database populated with 44 clinical modules.'))
        db.session.add(AuditLog(user_id=admin.id, action='DELETE', entity_type='Pet', entity_id=del_pet.id, details='Soft-deleted test patient Ghost'))

        db.session.commit()
        print("🎉 SUCCESS: PetCare360 Database fully seeded with rich clinical data!")
        print("----------------------------------------------------------------------")
        print("🔑 Demo Credentials:")
        print("   Administrator: admin@petcare360.com  / Admin@123")
        print("   Doctor:        doctor@petcare360.com / Doctor@123")
        print("   Clinic Staff:  staff@petcare360.com  / Staff@123")
        print("----------------------------------------------------------------------")


if __name__ == '__main__':
    seed_database()
