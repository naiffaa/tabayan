
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ---------------------------------------------------------------
# 1. تعريف مسار قاعدة البيانات (PostgreSQL ثابت)
# ---------------------------------------------------------------

# **ملاحظة هامة:** يرجى استبدال هذا المسار بمسار الاتصال الفعلي الخاص بك 
# (اسم المستخدم وكلمة المرور واسم قاعدة البيانات)
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:1234@localhost:5432/tabayyanDatabase"

# ---------------------------------------------------------------
# 2. إنشاء المحرك والجلسة
# ---------------------------------------------------------------

# إنشاء المحرك لـ PostgreSQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# إنشاء مُنشئ الجلسات
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# إنشاء القاعدة الأساسية (تُستخدم لتعريف النماذج في database_models.py)
Base = declarative_base()
