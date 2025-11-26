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
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

if TYPE_CHECKING:
    from brewing.db import Database


class Base(DeclarativeBase):
    pass


class Order(MappedAsDataclass, Base, kw_only=True, init=False):
    __tablename__ = "order"

    order_id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(30))
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    order_items: Mapped[list[OrderItem]] = relationship(
        cascade="all, delete-orphan", backref="order"
    )

    def __init__(self, customer_name: str) -> None:
        self.customer_name = customer_name
        self.order_date = datetime.now(UTC)


class Item(MappedAsDataclass, Base, kw_only=True, init=False):
    __tablename__ = "item"
    item_id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(30))
    price: Mapped[float]

    def __init__(self, description: str, price: float) -> None:
        self.description = description
        self.price = price

    def __repr__(self) -> str:
        return f"Item({self.description!r}, {self.price!r})"


class OrderItem(MappedAsDataclass, Base, kw_only=True, init=False):
    __tablename__ = "orderitem"
    order_id: Mapped[int] = mapped_column(
        ForeignKey("order.order_id"), primary_key=True
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("item.item_id"), primary_key=True)
    price: Mapped[float]

    def __init__(self, item: Item, price: float | None = None) -> None:
        self.item = item
        self.price = price or item.price

    item: Mapped[Item] = relationship(lazy="joined")


async def run_sample(db: Database):
    async with db.session() as session:
        # create catalog
        tshirt, mug, hat, crowbar = (
            Item("SA T-Shirt", 10.99),
            Item("SA Mug", 6.50),
            Item("SA Hat", 8.99),
            Item("MySQL Crowbar", 16.99),
        )
        session.add_all([tshirt, mug, hat, crowbar])
        await session.commit()

        # create an order
        order = Order("john smith")

        # add three OrderItem associations to the Order and save
        order.order_items.append(OrderItem(mug))
        order.order_items.append(OrderItem(crowbar, 10.99))
        order.order_items.append(OrderItem(hat))
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
