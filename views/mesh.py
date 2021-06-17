from views.general import UserModelView
from models.mesh import Mesh
from flask_admin import form
from wtforms import ValidationError

# class MeshUploadField(form.FileUploadField):
#     def pre_validate(self, form):
#         if self._is_uploaded_file(self.data) and not self.is_file_allowed(
#             self.data.filename
#         ):
#             raise ValidationError("Invalid file extension")
#
#     def _delete_file(self, filename):
#         return filename
#
#     def populate_obj(self, obj, name):
#         if self._is_uploaded_file(self.data):
#             filename = self.generate_name(obj, self.data)
#             filename = self._save_file(self.data, filename)
#             # update filename of FileStorage to our validated name
#             self.data.filename = filename
#             setattr(obj, name, filename)
#             setattr(obj, "file_bucket", self.base_path)
#
#     def _save_file(self, data, filename, base_path="."):
#
#         s3.Bucket(bucket).Object(self.data.filename).put(Body=data.read())
#
#         return self.data.filename


class MeshView(UserModelView):
    can_edit = False
    column_list = (
        Mesh.id,
        "project",
        Mesh.name,
        Mesh.zipfile,
        "odmproject",
        Mesh.status,
    )

    column_labels = {
        "name": "Mesh name",
        "zipfile": "Zip file"
    }
    column_descriptions = {
    }
    form_columns = (
        "project",
        Mesh.name,
        "odmproject",
        Mesh.zipfile,
    )
    form_extra_fields = {"zipfile": form.FileUploadField("Mesh zipfile", base_path="mesh", allowed_extensions=["zip"])}
    # if you want to edit project list, create, update, or detail view, specify adapted templates below.
    list_template = "mesh/list.html"
    create_template = "mesh/create.html"
    #edit_template = "project/edit.html"
    details_template = "mesh/details.html"
