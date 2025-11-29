"""Adapated test sample based on sqlalchemy sample.

see: https://docs.sqlalchemy.org/en/20/_modules/examples/association/basic_association.html

Illustrate a many-to-many relationship between an
"Order" and a collection of "Item" objects, associating a purchase price
with each via an association object called "OrderItem"

The association object pattern is a form of many-to-many which
associates additional data with each association between parent/child.

The example illustrates an "order", referencing a collection
of "items", with a particular price paid associated with each "item".

"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from brewing.db import db_session, new_base

Base = new_base()


class Order(Base):
    order_id: Mapped[int] = mapped_column(
        primary_key=True, init=False, autoincrement=True
    )
    customer_name: Mapped[str] = mapped_column(String(30))
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), init=False, default_factory=lambda: datetime.now(UTC)
    )
    order_items: Mapped[list[OrderItem]] = relationship(
        cascade="all, delete-orphan", backref="order", init=False
    )


class Item(Base):
    item_id: Mapped[int] = mapped_column(
        primary_key=True, init=False, autoincrement=True
    )
    description: Mapped[str] = mapped_column(String(30), init=True)
    price: Mapped[float] = mapped_column(init=True)


_PRICE_UNDEFINED = -1  # Sentinel for price not being explicitelyd defined


class OrderItem(Base, MappedAsDataclass, kw_only=True):
    order_id: Mapped[int] = mapped_column(
        ForeignKey("order.order_id"), primary_key=True, init=False
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("item.item_id"), primary_key=True, init=False
    )
    price: Mapped[float] = mapped_column(default=_PRICE_UNDEFINED)
    item: Mapped[Item] = relationship(lazy="joined")

    def __post_init__(self):
        if self.price is _PRICE_UNDEFINED:
            self.price = self.item.price


async def run_sample():
    async with db_session() as session:
        # create catalog
        tshirt, mug, hat, crowbar = (
            Item(description="SA T-Shirt", price=10.99),
            Item(description="SA Mug", price=6.50),
            Item(description="SA Hat", price=8.99),
            Item(description="MySQL Crowbar", price=16.99),
        )
        session.add_all([tshirt, mug, hat, crowbar])
        await session.commit()

        # create an order
        order = Order(customer_name="john smith")

        # add three OrderItem associations to the Order and save
        order.order_items.append(OrderItem(item=mug))
        order.order_items.append(OrderItem(item=crowbar, price=10.99))
        order.order_items.append(OrderItem(item=hat))
        session.add(order)
        await session.commit()

        # query the order, print items
        order = (
            await session.execute(select(Order).filter_by(customer_name="john smith"))
        ).scalar_one()

        # print customers who bought 'MySQL Crowbar' on sale
        (
            select(Order)
            .join(OrderItem)
            .join(Item)
            .where(
                Item.description == "MySQL Crowbar",
                Item.price > OrderItem.price,
            )
        )
