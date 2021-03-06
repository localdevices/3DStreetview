from flask import request, redirect, flash, has_app_context
from flask_security import current_user
from flask_admin import expose
from flask_admin.babel import gettext
from flask_admin.model.template import EndpointLinkRowAction
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_admin.helpers import is_form_submitted, validate_form_on_submit
from werkzeug.datastructures import ImmutableMultiDict
from wtforms import fields
from streetview.views.general import UserModelView
from streetview.models.mesh import Mesh
from streetview.models.odm import Odm
from streetview.models.odk import Odk
from odk2odm import odm_requests
from streetview.views.elements import odm_options

class MeshView(UserModelView):
    def render(self, template, **kwargs):
        """
        Modification of the default render method of flask admin ModelView.render.
        This modification ensures that also odm and odk server configurations that the currnetly logged in user owns
        are passed into the render view, so that they are available in the jinja2 templates. This is only relevant
        for the details and create templates.
        :param template: the specific view template that is to be rendered
        :param kwargs: keyword arguments passed to original render function
        :return:
        """
        # add a database query to available data in Jinja template in the edit page
        # example modified from https://stackoverflow.com/questions/65892714/pass-other-object-data-into-flask-admin-model-view-edit-template
        if template in ['mesh/details.html', 'mesh/create.html']:
            # filter out odm and odk configs that belong to currently logged in user
            odmconfigs = Odm.query.filter(Odm.user_id == current_user.id).all()
            odkconfigs = Odk.query.filter(Odk.user_id == current_user.id).all()
            # add odm config and odk config to variables available in jinja template
            kwargs["odm_configs"] = odmconfigs
            kwargs["odk_configs"] = odkconfigs
        return super(MeshView, self).render(template, **kwargs)

    # the details view must be shown as a modal instead of a new page
    details_modal = True
    can_edit = True

    @property
    def column_list(self):
        """
        Modify the displayed details in case a user is logged in as admin
        :return: user column list
        """
        user_column_list = [
            Mesh.id,
            Mesh.latitude,
            Mesh.longitude,
            Mesh.name,
            # Mesh.zipfile,
            Mesh.status,
            "odmproject_id",
            "odkproject_id",
        ]
        if has_app_context() and current_user.has_role('admin'):
            user_column_list.append("user")
        return user_column_list

    @property
    def _list_columns(self):
        return self.get_list_columns()

    @_list_columns.setter
    def _list_columns(self, value):
        pass

    @property
    def form_columns(self):
        """
        Modify the displayed details in case a user is logged in as admin
        :return: user form columns
        """
        user_form_columns = [
            Mesh.latitude,
            Mesh.longitude,
            Mesh.name,
            # "zipfile",
            "odmproject_id",
            "odkproject_id",
        ]
        if has_app_context() and current_user.has_role('admin'):
            user_form_columns.append("user")
        return user_form_columns

    # update associated form class properties
    @property
    def _create_form_class(self):
        return self.get_create_form()

    @_create_form_class.setter
    def _create_form_class(self, value):
        pass

    @property
    def _edit_form_class(self):
        return self.get_edit_form()

    @_edit_form_class.setter
    def _edit_form_class(self, value):
        pass

    column_labels = {
        "name": "Mesh name",
        # "zipfile": "Zip file",
    }
    # column_descriptions = {
    # }
    form_extra_fields = {
        "odmproject_id": fields.HiddenField("odmproject_id"),
        "odkproject_id": fields.HiddenField("odkproject_id"),
        # "zipfile": form.FileUploadField("Mesh zipfile", base_path="mesh", allowed_extensions=["zip"]),
    }

    column_extra_row_actions = [  # Add a new action button
        EndpointLinkRowAction("fa fa-exchange", ".odk2odm"),
    ]


    # if you want to edit project list, create, update, or detail view, specify adapted templates below.
    list_template = "mesh/list.html"
    create_template = "mesh/create.html"
    details_modal_template = "mesh/details.html"
    edit_template = "mesh/edit.html"
    odk2odm_template = "mesh/odk2odm.html"

    # def validate_form(self, form):
    #     if is_form_submitted():
    #         # do something
    #         print("Y'ello")
    #     return super(MeshView, self).validate_form(form)

    @expose("/odk2odm", methods=("GET", "POST"))
    def odk2odm(self):
        """
        A special odk2odm template, that performs the task of transferring files from ODK to ODM
        The template also allows for transfer of local photos to the same ODM tasks.
        """

        return_url = get_redirect_target() or self.get_url('.index_view')

        # odk2odm behaves the same as details
        if not self.can_view_details:
            return redirect(return_url)

        # retrieve mesh model
        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)
        model = self.get_one(id)
        if model is None:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)
        # establish a special form for odm options
        # retrieve latest ODM settings available
        odm_config = model.odmproject.odm
        options = odm_requests.get_options(odm_config.url, odm_config.token).json()
        default_options = odm_options.parse_default_options(options)
        options_fields = odm_options.get_options_fields(options, sort="name")
        # monkey patch OdmOptionsForm using the most current API based nodeODM settings available

        for k, v in options_fields.items():
            setattr(odm_options.OdmOptionsForm, k, v)
        form = odm_options.OdmForm()
        if request.method == "POST":
            # POST occurs when a user wants to upload local files to ODM server, or wants to make a new ODM task
            if "id" in request.form:
                # a photo upload is submitted
                task_id = request.form["id"]
                if task_id:
                    for f in request.files.getlist("file"):
                        print(f"Uploading file {f}")
                        # rewind to start of file
                        f.stream.seek(0)
                        files = {"images": (f.filename, f.stream, "images/jpg")}
                        res = model.odmproject.upload_file(task_id=request.form["id"], fields=files)
                else:
                    res = "No ODM task selected yet", 403
                return res # redirect(return_url)
            elif "task_form-name" in request.form:
                # A ODM task form is submitted
                if form.options_form.validate(form) and form.task_form.validate(form):
                    project_id = model.odmproject.remote_id
                    odm = model.odmproject.odm
                    # setup request data
                    data = {
                        "name": form.task_form["name"].data,
                        "partial": True,
                        "options": odm_options.parse_options(form.options_form, default_options=default_options)
                    }
                    res = odm_requests.post_task(odm.url, odm.token, project_id, data=data)
                    flash(f"New task with id {res.json()['id']} created")

                else:
                    flash("ODM task form is invalid, please rectify the errors", "error")

        template = self.odk2odm_template
        return self.render(
            template,
            model=model,
            details_columns=self._details_columns,
            get_value=self.get_detail_value,
            return_url=return_url,
            form=form,
        )
    def get_action_form(self):
        """
        Override the action form to enable submission of local files

        :return: form
        """
        form = super(UserModelView, self).get_action_form()
        form.files = fields.MultipleFileField('Select local Image(s)')
        form.upload = fields.SubmitField("Upload")
        return form

    def get_query(self):
        """
        Only show Odm configs from this user.

        :return: queried data
        """
        if not(current_user.has_role("admin")):
            return super(MeshView, self).get_query().filter(Mesh.user_id == current_user.id)
        else:
            return super(MeshView, self).get_query()

    def get_one(self, id):
        """
        Don't allow to access a specific Odm config if it's not from this user.

        :param id: id of model
        :return: first in query
        """
        if not(current_user.has_role("admin")):
            return super(MeshView, self).get_query().filter_by(id=id).filter(Mesh.user_id == current_user.id).one()
        else:
            return super(MeshView, self).get_query().filter_by(id=id).one()


    def on_model_change(self, form, model, is_created):
        """
        Link newly created Odm config to the current logged in user on creation.

        :param form: form object
        :param model: database model
        :param is_created: True when a new model is created from form
        """
        if is_created:
            model.user_id = current_user.id
