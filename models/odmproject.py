from sqlalchemy import Integer, ForeignKey, String, Column
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.orm import relationship
from models.base import Base
from odk2odm import odm_requests

class Odmproject(Base, SerializerMixin):
    """
    Association table, for associating an ODM project to a Mesh record. Currently assumed to be a
    one-to-one relationship.
    The full table of projects available for association should be retrieved with the ODM API
    """
    __tablename__ = "odmproject"
    serialize_only = ('id', 'odm_id', 'remote_id')
    id = Column(Integer, primary_key=True)
    odm_id = Column(Integer, ForeignKey("odm.id"), nullable=False)
    remote_id = Column(Integer, nullable=False)
    odm = relationship("Odm")

    @property
    def project(self):
        return odm_requests.get_project(self.odm.url, token=self.odm.token, project_id=self.remote_id).json()



    def __str__(self):
        return "{}".format(self.remote_id)

    def __repr__(self):
        return "{}: {}".format(self.id, self.__str__())
