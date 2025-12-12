from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base

# القاعدة الأساسية لتعريف النماذج
Base = declarative_base()

# ---------------------------------------------------------------
# جدول العمليات (Operation)
# ---------------------------------------------------------------
class Operation(Base):
    """
    نموذج SQLAlchemy لجدول 'operations' في قاعدة البيانات.
    يخزن تفاصيل العملية النقدية وحالتها ونتائج تحليل الذكاء الاصطناعي.
    """
    __tablename__ = "operations"

    # الحقول الأساسية
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False, index=True)
    employee_name = Column(String, index=True, nullable=False)
    description = Column(String)
    verification_method = Column(String, nullable=False)
    
    # حقول نظام "تبيّن"
    source = Column(String, default="web") # مصدر الإدخال: 'web' أو 'hardware'
    status = Column(String, default="pending", index=True) # حالة العملية: approved, suspicious, reviewed, rejected

    # حقل نتيجة الذكاء الاصطناعي (خانة الموديل)
    is_suspicious = Column(Boolean, default=False, index=True) 

    # حقل المراجعة
    notes = Column(String) # ملاحظات يدوية من المدقق/المراجع
    
    # حقول التوقيت
    # يستخدم func.now() لتعيين الوقت والتاريخ من جانب قاعدة البيانات
    created_at = Column(DateTime, default=func.now()) 

    # إعادة تعريف التمثيل النصي
    def __repr__(self):
        return f"<Operation(id={self.id}, amount={self.amount}, status='{self.status}')>"

# ملاحظة: تم حذف جدول 'Product' القديم واستبداله بـ 'Operation'