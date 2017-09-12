from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import scoped_session, sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    email = Column(String(100), nullable=False, unique=True)
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)


class Category(Base):
    __tablename__ = "categories"
    name = Column(String(100), nullable=False)
    id = Column(Integer, primary_key=True)


class Item(Base):
    __tablename__ = 'item'
    name = Column(String(100), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    user = relationship(User)
    category = relationship(Category)

    @property
    def sirlize(self):
        return {
            'name': self.name,
            'id': self.id,
            'description': self.description,
            'created': self.created,
            'user': self.user.name,
            'title': self.category.name
        }


engine = create_engine('postgresql://catalogs:password@localhost/catalogs')
Base.metadata.create_all(engine)

session__ = sessionmaker(autocommit=False,
                         autoflush=False,
                         bind=engine)

db = scoped_session(session__)

session__ = session__()
