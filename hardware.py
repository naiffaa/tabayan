import serial
import time
import threading
from typing import Optional, Dict, Any


SERIAL_PORT = 'COM3'  
BAUD_RATE = 9600
DATA_PREFIX = "CLIENT_DATA:"


LAST_SCANNED_CUSTOMER: Optional[Dict[str, str]] = None


stop_thread_event = threading.Event()
serial_thread: Optional[threading.Thread] = None

def read_serial_data():

    global LAST_SCANNED_CUSTOMER

    try:
        
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) 
        print(f"[{threading.current_thread().name}] تم الاتصال بـ {SERIAL_PORT}...")

        while not stop_thread_event.is_set():
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()

                if line.startswith(DATA_PREFIX):
                    raw_data = line[len(DATA_PREFIX):]

                    parts = raw_data.split(',')
                    
                    if len(parts) == 3:
                        customer_name = parts[0].strip()
                        customer_id = parts[1].strip()
                        customer_phone = parts[2].strip()

                        LAST_SCANNED_CUSTOMER = {
                            "name": customer_name,
                            "id": customer_id,
                            "phone": customer_phone,
                            "uid_read_at": datetime.now().isoformat()
                        }
                        
                        print(f"[{threading.current_thread().name}] تم مسح عميل: {customer_name}")
                        time.sleep(0.5)
                    else:
                        print(f"[{threading.current_thread().name}] خطأ في تنسيق البيانات: {raw_data}")

                time.sleep(0.01)

    except serial.SerialException as e:
        print(f"[{threading.current_thread().name}] خطأ فادح في الاتصال: {e}")
    except Exception as e:
        print(f"[{threading.current_thread().name}] خطأ غير متوقع: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
        print(f"[{threading.current_thread().name}] تم إغلاق خيط القراءة التسلسلية.")


def start_serial_thread():
    global serial_thread
    if serial_thread is None or not serial_thread.is_alive():
        stop_thread_event.clear()
        serial_thread = threading.Thread(target=read_serial_data, name="SerialReaderThread")
        serial_thread.daemon = True # يضمن إغلاق الخيط عند إغلاق التطبيق الرئيسي
        serial_thread.start()
        print("بدء تشغيل Serial...")

def stop_serial_thread():
    global serial_thread
    if serial_thread and serial_thread.is_alive():
        stop_thread_event.set()
        serial_thread.join(timeout=3) # الانتظار لثلاث ثواني لإغلاق الخيط
        print("تم إيقاف Serial.")