# بداية main.py
import os
import pandas as pd
import numpy as np 
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, String  # <<-- تأكد من وجود String هنا
from joblib import load
from pydantic import BaseModel
from datetime import datetime, timedelta
import hardware 
import models
import database_models
import database
from database import engine 

database_models.Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="نظام تبيّن - API",
    description="واجهة برمجية لإدارة وتوثيق العمليات النقدية ومكافحة غسل الأموال.",
    docs_url="/docs",
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MODEL_PATH = "tabayyun_anomaly_model.joblib"
SCALER_PATH = "tabayyun_scaler.joblib"

try:
    anomaly_model = load(MODEL_PATH)
    scaler = load(SCALER_PATH)
    print("AI Model and Scaler loaded successfully.")
except FileNotFoundError:
    print("WARNING: AI Model files not found. Anomaly detection will be disabled.")
    anomaly_model = None
    scaler = None
except Exception as e:
    print(f"Error loading AI Model: {e}")
    anomaly_model = None
    scaler = None

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_anomaly_detection(operation_data: models.OperationBase) -> bool:
    """
    تشغيل نموذج الذكاء الاصطناعي ببناء الـ 12 خاصية بالترتيب الدقيق:
    ['Total_Amount', 'Amount_Z_Score', ..., 'Payment_Category_Utilities']
    """
    if anomaly_model is None or scaler is None:
        print("AI Model or Scaler not loaded.")
        return False
        
    try:
        current_time = datetime.now()
        
        
        historical_avg = 100.0 
        historical_std = 50.0  
        
        if historical_std == 0:
            amount_z_score = 0
        else:
            amount_z_score = (operation_data.amount - historical_avg) / historical_std
        
        
        cat_luxury = 0.0
        cat_services = 0.0
        cat_travel = 0.0
        cat_utilities = 0.0
        
        method = operation_data.verification_method
        
        if method == 'Luxury':
            cat_luxury = 1.0
        elif method == 'Services':
            cat_services = 1.0
        elif method == 'Travel':
            cat_travel = 1.0
        elif method == 'Utilities':
            cat_utilities = 1.0

        
        raw_features = [
            operation_data.amount,             # 1. Total_Amount
            amount_z_score,                    # 2. Amount_Z_Score
            historical_avg,                    # 3. Person_Avg_Amount
            historical_std,                    # 4. Person_Std_Dev
            24.0,                              # 5. Time_Since_Last 
            float(current_time.weekday()),     # 6. Day_of_Week
            float(current_time.hour),          # 7. Hour_of_Day
            1.0,                               # 8. New_Vendor_Flag
            cat_luxury,                        # 9. Payment_Category_Luxury
            cat_services,                      # 10. Payment_Category_Services
            cat_travel,                        # 11. Payment_Category_Travel
            cat_utilities                      # 12. Payment_Category_Utilities
        ]
        
        X_new = np.array([raw_features])
        
        X_new_scaled = scaler.transform(X_new)
        prediction = anomaly_model.predict(X_new_scaled)
        
        is_suspicious = prediction[0] == -1
        
        print(f"\n--- AI Check ---")
        print(f"Total Amount: {operation_data.amount}, Z-Score: {amount_z_score:.2f}")
        print(f"Prediction Label (-1 is anomaly): {prediction[0]}")
        print(f"Is Suspicious: {is_suspicious}")

        return is_suspicious
        
    except Exception as e:
        print(f"CRITICAL ERROR in AI detection: {e}")
        return False
    
    
# ---------------------------------------------------------------
# 3. نماذج إضافية (محلية)
# ---------------------------------------------------------------
class UserLogin(BaseModel):
    commercial_id: str 
    password: str

class LoginResponse(BaseModel):
    message: str
    token: str 


# ---------------------------------------------------------------
# 4. مسارات المصادقة (Authentication Endpoints)
# ---------------------------------------------------------------
@app.post("/auth/login", response_model=LoginResponse)
def login_for_access_token(user_credentials: UserLogin, db: Session = Depends(get_db)):
    # هنا يتم التحقق من رقم السجل التجاري وكلمة المرور في قاعدة البيانات
    # مثال بسيط جداً للمحاكاة (يجب استبداله بمنطق توثيق JWT)
    if user_credentials.commercial_id == "12345" and user_credentials.password == "securepass":
        # في بيئة حقيقية، سيتم إنشاء رمز JWT هنا
        return {"message": "تم تسجيل الدخول بنجاح", "token": "FAKE_JWT_TOKEN"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بيانات الدخول غير صحيحة",
        headers={"WWW-Authenticate": "Bearer"},
    )

# ---------------------------------------------------------------
# 5. مسارات العمليات (Operations CRUD Endpoints)
# ---------------------------------------------------------------

@app.get("/operations/", response_model=List[models.Operation])
def get_operations(
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None)
):
    query = db.query(database_models.Operation)

    if status_filter:
        query = query.filter(database_models.Operation.status == status_filter)
        
    if search:
        query = query.filter(
            (database_models.Operation.id.cast(String).contains(search)) |
            (database_models.Operation.employee_name.ilike(f"%{search}%")) |
            (database_models.Operation.description.ilike(f"%{search}%"))
        )
    
    operations = query.order_by(database_models.Operation.created_at.desc()).all()
    return operations

@app.post("/operations/", response_model=models.Operation, status_code=status.HTTP_201_CREATED)
def create_operation(
    operation: models.OperationCreate, 
    source: str = "web", 
    db: Session = Depends(get_db)
):
    ai_suspicious = run_anomaly_detection(operation)
    
    CASH_THRESHOLD = 50000.0
    threshold_suspicious = operation.amount >= CASH_THRESHOLD
    is_suspicious = ai_suspicious or threshold_suspicious
    
    operation_status = "suspicious" if is_suspicious else "approved"
    if threshold_suspicious:
        print(f"ALERT: Operation amount {operation.amount} exceeded cash threshold {CASH_THRESHOLD}.")
    
    db_operation = database_models.Operation(
        **operation.model_dump(),
        source=source,
        is_suspicious=is_suspicious,
        status=operation_status
    )
    
    db.add(db_operation)
    db.commit()
    db.refresh(db_operation)
    return db_operation

@app.put("/operations/{operation_id}", response_model=models.Operation)
def update_operation(operation_id: int, operation: models.OperationUpdate, db: Session = Depends(get_db)):
    db_operation = db.query(database_models.Operation).filter(database_models.Operation.id == operation_id).first()
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Operation not found")
    
    update_data = operation.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_operation, key, value)
        
    db.add(db_operation)
    db.commit()
    db.refresh(db_operation)
    return db_operation

@app.delete("/operations/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_operation(operation_id: int, db: Session = Depends(get_db)):
    db_operation = db.query(database_models.Operation).filter(database_models.Operation.id == operation_id).first()
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Operation not found")
        
    db.delete(db_operation)
    db.commit()
    return {"ok": True}

# ---------------------------------------------------------------
# 6. مسارات الإحصائيات والتنبيهات (Dashboard & Alerts Endpoints)
# ---------------------------------------------------------------

@app.get("/stats/summary/", response_model=Dict[str, Any])
def get_dashboard_summary(db: Session = Depends(get_db)):
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # 1. إجمالي النقد اليوم
    total_cash_today = db.query(func.sum(database_models.Operation.amount)).filter(
        func.date(database_models.Operation.created_at) == today
    ).scalar() or 0
    
    # 2. العمليات اليومية
    total_ops_today = db.query(func.count(database_models.Operation.id)).filter(
        func.date(database_models.Operation.created_at) == today
    ).scalar()
    
    # 3. عمليات الأمس لحساب النسبة المئوية
    total_ops_yesterday = db.query(func.count(database_models.Operation.id)).filter(
        func.date(database_models.Operation.created_at) == yesterday
    ).scalar() or 1 # تجنب القسمة على صفر
    
    approved_ops_count = db.query(func.count(database_models.Operation.id)).filter(
        func.date(database_models.Operation.created_at) == today,
        database_models.Operation.status == 'approved'
    ).scalar()
    
    compliance_rate = (approved_ops_count / total_ops_today) * 100 if total_ops_today else 0
    
    op_change_percent = ((total_ops_today - total_ops_yesterday) / total_ops_yesterday) * 100
    
    return {
        "total_cash_today": round(total_cash_today, 2),
        "total_operations_today": total_ops_today,
        "compliance_rate": round(compliance_rate, 1),
        "operation_change_percent": round(op_change_percent, 1),
    }

@app.get("/alerts/", response_model=List[models.Operation])
def get_suspicious_alerts(db: Session = Depends(get_db)):
    """
    جلب جميع العمليات التي تم تصنيفها كـ 'مشبوهة' بواسطة الذكاء الاصطناعي.
    """
    alerts = db.query(database_models.Operation).filter(
        database_models.Operation.is_suspicious == True
    ).order_by(database_models.Operation.created_at.desc()).all()
    
    return alerts


@app.get("/analytics/cash_flow_daily/", response_model=List[Dict[str, Any]])
def get_daily_cash_flow(db: Session = Depends(get_db)):
    """
    جلب حركة النقد اليومية لآخر 7 أيام للرسم البياني في لوحة التحكم.
    """
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    results = db.query(
        func.date(database_models.Operation.created_at).label("date"),
        func.sum(database_models.Operation.amount).label("total_cash")
    ).filter(
        database_models.Operation.created_at >= seven_days_ago
    ).group_by(
        func.date(database_models.Operation.created_at)
    ).order_by("date").all()
    
    # تحويل النتائج إلى قائمة قواميس
    return [
        {"date": r.date.strftime("%Y-%m-%d"), "amount": round(r.total_cash, 2)} 
        for r in results
    ]


# ---------------------------------------------------------------
# 7. مسار الإعدادات (Settings Endpoint)
# ---------------------------------------------------------------
# هذا المسار يستخدم للتحديث (PUT) لإعدادات المنشأة وتفعيل/إيقاف AI
@app.put("/settings/", status_code=status.HTTP_200_OK)
def update_settings(settings: Dict[str, Any]):
    """
    مسار وهمي لتحديث الإعدادات (تفعيل/إيقاف AI) - 
    في تطبيق حقيقي، سيتم حفظ هذه الإعدادات في جدول مخصص.
    """
    if "ai_alerts_enabled" in settings:
        print(f"AI Alerts set to: {settings['ai_alerts_enabled']}")
    
    return {"message": "تم حفظ الإعدادات بنجاح"}



app = FastAPI(
    title="نظام تبيّن - API",
    description="واجهة برمجية لإدارة وتوثيق العمليات النقدية ومكافحة غسل الأموال.",
    docs_url="/docs",
    redoc_url=None
)
# ... (بقية الـ CORS كما هي)

# *****************************************
# ⬅️ 2. خطافات أحداث التطبيق (Startup/Shutdown Events)
# *****************************************

@app.on_event("startup")
def startup_event():
    # تشغيل خيط قراءة المنفذ التسلسلي عند بدء التطبيق
    hardware.start_serial_thread()

@app.on_event("shutdown")
def shutdown_event():
    # إيقاف خيط قراءة المنفذ التسلسلي بأمان عند إغلاق التطبيق
    hardware.stop_serial_thread()
    
# ... (بقية تحميل نموذج AI)

# ... (بقية دالة get_db)

# ... (بقية دالة run_anomaly_detection)

# ... (بقية نماذج Pydantic)

# ... (بقية مسارات Authentication و Operations CRUD)


# ---------------------------------------------------------------
# 8. مسارات قارئ RFID (New RFID Scanner Endpoints)
# ---------------------------------------------------------------

# نموذج Pydantic للرد على طلب المسح
class ScanResponse(BaseModel):
    name: str
    id: str
    phone: str
    uid_read_at: str
    message: str = "تم العثور على عميل مطابق لبطاقة RFID الممسوحة."

@app.get("/scan/get_customer_data/", response_model=Optional[ScanResponse])
def get_scanned_customer_data():
    """
    مسار API تستدعيه الواجهة الأمامية للحصول على بيانات العميل
    الذي تم مسح بطاقته مؤخراً عبر منفذ Serial.
    """
    customer_data = hardware.LAST_SCANNED_CUSTOMER
    
    if customer_data:
        # نقوم بمسح البيانات فوراً بعد إرسالها لتجنب إعادة إرسالها مرة أخرى
        # في حال استدعى الفرونت إند نفس المسار بدون مسح بطاقة جديدة.
        hardware.LAST_SCANNED_CUSTOMER = None 
        
        return ScanResponse(
            name=customer_data["name"],
            id=customer_data["id"],
            phone=customer_data["phone"],
            uid_read_at=customer_data["uid_read_at"]
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="لم يتم مسح بطاقة RFID جديدة بعد أو لم يتم العثور على عميل مطابق."
    )
