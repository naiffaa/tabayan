from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ---------------------------------------------------------------
# 1. OperationBase: الحقول المشتركة للعملية
# ---------------------------------------------------------------
class OperationBase(BaseModel):
    """النموذج الأساسي لبيانات العملية النقدية."""
    
    # حقول بيانات العملية الأساسية
    amount: float = Field(..., gt=0, description="المبلغ الإجمالي للعملية النقدية.")
    employee_name: str = Field(..., description="اسم الموظف الذي قام بالتوثيق.")
    description: Optional[str] = Field(None, description="وصف قصير أو ملاحظات حول العملية.")
    
    # حقل التوثيق (مهم للتفريق بين أنواع الإدخال)
    verification_method: str = Field(..., description="طريقة توثيق العميل (مثل ID, QR, Card).")
    
    # حقول الذكاء الاصطناعي (يتم إدخالها من الباك إند عادةً، لكن نحتاجها في البنية)
    # ملاحظة: سنستخدم المبلغ كمدخل رئيسي لنموذج الذكاء الاصطناعي في main.py
    
    class Config:
        # يتيح استخدام نماذج SQLAlchemy مباشرة مع Pydantic
        from_attributes = True


# ---------------------------------------------------------------
# 2. OperationCreate: النموذج المستخدم لإنشاء عملية جديدة (POST)
# ---------------------------------------------------------------
class OperationCreate(OperationBase):
    """النموذج المستخدم لإنشاء عملية جديدة عبر API."""
    pass


# ---------------------------------------------------------------
# 3. OperationUpdate: النموذج المستخدم لتحديث عملية موجودة (PUT)
# ---------------------------------------------------------------
class OperationUpdate(BaseModel):
    """النموذج المستخدم لتحديث عملية موجودة (لتعديل الحالة أو الملاحظات)."""
    
    status: Optional[str] = Field(None, description="حالة العملية: 'approved', 'suspicious', 'reviewed', 'rejected'.")
    notes: Optional[str] = Field(None, description="ملاحظات الموظف أو المدقق.")
    

# ---------------------------------------------------------------
# 4. Operation: النموذج الكامل الذي يتم إرجاعه من API (GET)
# ---------------------------------------------------------------
class Operation(OperationBase):
    """النموذج الكامل للعملية كما يتم عرضه للمستخدم."""
    
    id: int = Field(..., description="رقم تعريف العملية الفريد.")
    
    # حقول إضافية يتم تحديدها بواسطة النظام أو الذكاء الاصطناعي
    source: str = Field(..., description="مصدر الإدخال: 'web' (الموقع) أو 'hardware' (جهاز الأردوينو).")
    status: str = Field(..., description="الحالة النهائية للعملية.")
    is_suspicious: bool = Field(False, description="نتيجة الموديل: هل العملية مشبوهة؟")
    
    # حقول التوقيت
    created_at: datetime = Field(..., description="تاريخ ووقت إنشاء العملية.")
    
    # ملاحظات المراجعة
    notes: Optional[str] = Field(None, description="ملاحظات المدقق حول العملية.")