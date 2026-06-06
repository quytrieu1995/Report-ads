# E-commerce Data Hub

Ứng dụng web chạy local để lưu trữ và báo cáo số liệu đa sàn thương mại điện tử (TikTok Shop, Shopee).

## Yêu cầu

- Python 3.10+
- Windows (dùng `run.bat`) hoặc macOS/Linux (chạy thủ công)

## Khởi chạy nhanh (Windows)

Double-click **`run.bat`** — script sẽ:

1. Tạo virtual environment `.venv` (lần đầu)
2. Cài dependencies từ `backend/requirements.txt`
3. Khởi động server tại http://localhost:8000 và mở trình duyệt

## Khởi chạy thủ công (macOS/Linux)

```bash
cd ecommerce-data-hub
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Mở http://127.0.0.1:8000 trong trình duyệt.

## Cấu trúc

```
ecommerce-data-hub/
├── run.bat              # One-click Windows
├── backend/
│   ├── main.py          # FastAPI API + phục vụ frontend
│   ├── database.py      # SQLite mặc định, đổi qua DATABASE_URL
│   ├── models.py        # Schema ORM
│   ├── parsers.py       # Nhận diện + chuẩn hoá dữ liệu
│   ├── ingest.py        # Nạp DB + chống trùng hash
│   └── requirements.txt
├── frontend/
│   └── index.html       # Dashboard vanilla JS
└── data/
    └── datahub.db       # SQLite (tự tạo)
```

## Nguồn dữ liệu hỗ trợ

| Loại | File | Nhận diện |
|------|------|-----------|
| TikTok đơn hàng | CSV | Cột `Order ID` + `Seller SKU` |
| TikTok quảng cáo | `Creative_data_*.xlsx` | `ID video` + `Loại nội dung sáng tạo` |
| TikTok affiliate creator | `Creator_List_*.xlsx` | `Tên người dùng...` + `GMV liên kết` |
| TikTok affiliate video | `Creator_Video_List_*.xlsx` | `Tên video` + creator username |
| Shopee shop stats | `*shopee-shop-stats*.xlsx` | Sheet `Đơn hàng đã đặt` hoặc cột doanh số |

Upload qua dashboard — hệ thống tự nhận diện loại file, không cần chọn thủ công.

## API

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/upload` | Upload nhiều file |
| GET | `/api/batches` | Lịch sử upload |
| DELETE | `/api/batches/{id}` | Xoá batch + dữ liệu |
| GET | `/api/summary` | KPI tổng hợp |
| GET | `/api/report/top-products` | Top sản phẩm TikTok |
| GET | `/api/report/top-creators` | Top creator affiliate |
| GET | `/api/report/shopee-daily` | Doanh số Shopee theo ngày |

## Cấu hình

- **SQLite** (mặc định): database tại `data/datahub.db`
- **PostgreSQL**: đặt biến môi trường `DATABASE_URL=postgresql://user:pass@host/db`

## Kiểm thử

```bash
cd ecommerce-data-hub
source .venv/bin/activate
python tests/test_sample_data.py
```
