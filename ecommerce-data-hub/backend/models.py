"""Schema ORM — upload_batch + 6 bảng fact."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class UploadBatch(Base):
    """Sổ đăng ký mọi lần upload file."""

    __tablename__ = "upload_batch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    period_start: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TiktokOrder(Base):
    """Đơn hàng TikTok Shop — cấp dòng SKU."""

    __tablename__ = "tiktok_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("upload_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    order_status: Mapped[Optional[str]] = mapped_column(String(128))
    order_substatus: Mapped[Optional[str]] = mapped_column(String(128))
    cancelation_return_type: Mapped[Optional[str]] = mapped_column(String(128))
    sku_id: Mapped[Optional[str]] = mapped_column(String(64))
    seller_sku: Mapped[Optional[str]] = mapped_column(String(256), index=True)
    product_name: Mapped[Optional[str]] = mapped_column(Text)
    variation: Mapped[Optional[str]] = mapped_column(String(512))
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    sku_quantity_of_return: Mapped[Optional[float]] = mapped_column(Float)
    sku_unit_original_price: Mapped[Optional[float]] = mapped_column(Float)
    sku_subtotal_before_discount: Mapped[Optional[float]] = mapped_column(Float)
    sku_platform_discount: Mapped[Optional[float]] = mapped_column(Float)
    sku_seller_discount: Mapped[Optional[float]] = mapped_column(Float)
    sku_subtotal_after_discount: Mapped[Optional[float]] = mapped_column(Float)
    shipping_fee_after_discount: Mapped[Optional[float]] = mapped_column(Float)
    original_shipping_fee: Mapped[Optional[float]] = mapped_column(Float)
    taxes: Mapped[Optional[float]] = mapped_column(Float)
    order_amount: Mapped[Optional[float]] = mapped_column(Float)
    order_refund_amount: Mapped[Optional[float]] = mapped_column(Float)
    created_time: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    paid_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    shipped_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    delivered_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cancelled_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text)
    fulfillment_type: Mapped[Optional[str]] = mapped_column(String(128))
    warehouse_name: Mapped[Optional[str]] = mapped_column(String(256))
    delivery_option: Mapped[Optional[str]] = mapped_column(String(128))
    shipping_provider_name: Mapped[Optional[str]] = mapped_column(String(256))
    buyer_username: Mapped[Optional[str]] = mapped_column(String(256))
    province: Mapped[Optional[str]] = mapped_column(String(128))
    district: Mapped[Optional[str]] = mapped_column(String(128))
    payment_method: Mapped[Optional[str]] = mapped_column(String(128))
    weight_kg: Mapped[Optional[float]] = mapped_column(Float)
    product_category: Mapped[Optional[str]] = mapped_column(String(256))


class TiktokAdCreative(Base):
    """Hiệu suất video quảng cáo TikTok."""

    __tablename__ = "tiktok_ad_creative"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("upload_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_id: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    video_title: Mapped[Optional[str]] = mapped_column(Text)
    tiktok_account: Mapped[Optional[str]] = mapped_column(String(256))
    creative_type: Mapped[Optional[str]] = mapped_column(String(128))
    video_source: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[Optional[str]] = mapped_column(String(64))
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cost: Mapped[Optional[float]] = mapped_column(Float)
    sku_order_count: Mapped[Optional[float]] = mapped_column(Float)
    cost_per_order: Mapped[Optional[float]] = mapped_column(Float)
    gross_revenue: Mapped[Optional[float]] = mapped_column(Float)
    roi: Mapped[Optional[float]] = mapped_column(Float)
    product_ad_impressions: Mapped[Optional[float]] = mapped_column(Float)
    product_ad_clicks: Mapped[Optional[float]] = mapped_column(Float)
    product_ad_ctr: Mapped[Optional[float]] = mapped_column(Float)
    ad_conversion_rate: Mapped[Optional[float]] = mapped_column(Float)
    view_rate_2s: Mapped[Optional[float]] = mapped_column(Float)
    view_rate_6s: Mapped[Optional[float]] = mapped_column(Float)
    view_rate_25pct: Mapped[Optional[float]] = mapped_column(Float)
    view_rate_50pct: Mapped[Optional[float]] = mapped_column(Float)
    view_rate_75pct: Mapped[Optional[float]] = mapped_column(Float)
    view_rate_100pct: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(16))


class TiktokAffiliateCreator(Base):
    """Nhà sáng tạo affiliate TikTok."""

    __tablename__ = "tiktok_affiliate_creator"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("upload_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    creator_username: Mapped[Optional[str]] = mapped_column(String(256), index=True)
    gmv: Mapped[Optional[float]] = mapped_column(Float)
    gmv_live: Mapped[Optional[float]] = mapped_column(Float)
    gmv_video: Mapped[Optional[float]] = mapped_column(Float)
    gmv_product_card: Mapped[Optional[float]] = mapped_column(Float)
    linked_products_sold: Mapped[Optional[float]] = mapped_column(Float)
    items_sold: Mapped[Optional[float]] = mapped_column(Float)
    estimated_commission: Mapped[Optional[float]] = mapped_column(Float)
    estimated_flat_fee: Mapped[Optional[float]] = mapped_column(Float)
    aov: Mapped[Optional[float]] = mapped_column(Float)
    linked_product_showcase: Mapped[Optional[float]] = mapped_column(Float)
    orders: Mapped[Optional[float]] = mapped_column(Float)
    ctr: Mapped[Optional[float]] = mapped_column(Float)
    product_impressions: Mapped[Optional[float]] = mapped_column(Float)
    avg_linked_customers: Mapped[Optional[float]] = mapped_column(Float)
    linked_live_sessions: Mapped[Optional[float]] = mapped_column(Float)
    linked_videos: Mapped[Optional[float]] = mapped_column(Float)
    gmv_collab: Mapped[Optional[float]] = mapped_column(Float)
    gmv_collab_target: Mapped[Optional[float]] = mapped_column(Float)
    commission_collab_target: Mapped[Optional[float]] = mapped_column(Float)
    gmv_collab_open: Mapped[Optional[float]] = mapped_column(Float)
    commission_collab_open: Mapped[Optional[float]] = mapped_column(Float)
    gmv_refunded: Mapped[Optional[float]] = mapped_column(Float)
    refunded_items: Mapped[Optional[float]] = mapped_column(Float)
    followers: Mapped[Optional[float]] = mapped_column(Float)


class TiktokAffiliateVideo(Base):
    """Video affiliate TikTok."""

    __tablename__ = "tiktok_affiliate_video"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("upload_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_name: Mapped[Optional[str]] = mapped_column(Text)
    posted_date: Mapped[Optional[datetime]] = mapped_column(Date)
    creator_username: Mapped[Optional[str]] = mapped_column(String(256), index=True)
    shoppable_comments: Mapped[Optional[float]] = mapped_column(Float)
    shoppable_likes: Mapped[Optional[float]] = mapped_column(Float)
    linked_orders: Mapped[Optional[float]] = mapped_column(Float)
    items_sold: Mapped[Optional[float]] = mapped_column(Float)
    shoppable_aov: Mapped[Optional[float]] = mapped_column(Float)
    gmv: Mapped[Optional[float]] = mapped_column(Float)
    gmv_video: Mapped[Optional[float]] = mapped_column(Float)
    estimated_commission: Mapped[Optional[float]] = mapped_column(Float)
    estimated_flat_fee: Mapped[Optional[float]] = mapped_column(Float)
    avg_linked_customers: Mapped[Optional[float]] = mapped_column(Float)
    refunded_items: Mapped[Optional[float]] = mapped_column(Float)
    gmv_refunded: Mapped[Optional[float]] = mapped_column(Float)
    shoppable_impressions: Mapped[Optional[float]] = mapped_column(Float)
    linked_ctr: Mapped[Optional[float]] = mapped_column(Float)
    shoppable_gpm: Mapped[Optional[float]] = mapped_column(Float)


class ShopeeShopDaily(Base):
    """Thống kê cửa hàng Shopee theo ngày."""

    __tablename__ = "shopee_shop_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("upload_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stat_date: Mapped[Optional[datetime]] = mapped_column(Date, index=True)
    order_type: Mapped[str] = mapped_column(String(32), index=True)
    total_sales: Mapped[Optional[float]] = mapped_column(Float)
    sales_excl_subsidy: Mapped[Optional[float]] = mapped_column(Float)
    total_orders: Mapped[Optional[float]] = mapped_column(Float)
    sales_per_order: Mapped[Optional[float]] = mapped_column(Float)
    product_clicks: Mapped[Optional[float]] = mapped_column(Float)
    visits: Mapped[Optional[float]] = mapped_column(Float)
    conversion_rate: Mapped[Optional[float]] = mapped_column(Float)
    cancelled_orders: Mapped[Optional[float]] = mapped_column(Float)
    cancelled_sales: Mapped[Optional[float]] = mapped_column(Float)
    return_orders: Mapped[Optional[float]] = mapped_column(Float)
    return_sales: Mapped[Optional[float]] = mapped_column(Float)
    buyers: Mapped[Optional[float]] = mapped_column(Float)
    new_buyers: Mapped[Optional[float]] = mapped_column(Float)
    existing_buyers: Mapped[Optional[float]] = mapped_column(Float)
    potential_buyers: Mapped[Optional[float]] = mapped_column(Float)
    buyer_return_rate: Mapped[Optional[float]] = mapped_column(Float)


class ShopeeProductStat(Base):
    """Thống kê sản phẩm Shopee."""

    __tablename__ = "shopee_product_stat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("upload_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    product_name: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(String(64))
    sales_ratio: Mapped[Optional[float]] = mapped_column(Float)
    sales: Mapped[Optional[float]] = mapped_column(Float)
    impressions: Mapped[Optional[float]] = mapped_column(Float)
    clicks: Mapped[Optional[float]] = mapped_column(Float)
    total_orders: Mapped[Optional[float]] = mapped_column(Float)
    items: Mapped[Optional[float]] = mapped_column(Float)
    ctr: Mapped[Optional[float]] = mapped_column(Float)
    conversion_rate: Mapped[Optional[float]] = mapped_column(Float)
    sales_per_order: Mapped[Optional[float]] = mapped_column(Float)
    buyers: Mapped[Optional[float]] = mapped_column(Float)


# Index bổ sung cho truy vấn báo cáo
Index("ix_tiktok_order_batch_created", TiktokOrder.batch_id, TiktokOrder.created_time)
Index("ix_shopee_daily_date_type", ShopeeShopDaily.stat_date, ShopeeShopDaily.order_type)
