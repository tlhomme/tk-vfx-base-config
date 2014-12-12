# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import uuid
import tempfile

import tank
from tank import Hook
from tank import TankError

import sys

LINUX_PATH = "/s/apps/common/python/luigi/infonodelib"
WINDOWS_PATH = "V:\\apps\\common\\python\\luigi\\infonodelib"
info_lib_path = {"linux2": LINUX_PATH,
              "win32":  WINDOWS_PATH,
              "darwin": "" }

sys.path.append(info_lib_path[sys.platform])

from infonodelib import InfoNodeLib

class PrimaryPublishHook(Hook):
    """
    Single hook that implements publish of the primary task
    """

    def execute(self, task, work_template, comment, thumbnail_path, sg_task, progress_cb, **kwargs):
        """
        Main hook entry point
        :param task:            Primary task to be published.  This is a
                                dictionary containing the following keys:
                                {
                                    item:   Dictionary
                                            This is the item returned by the scan hook
                                            {
                                                name:           String
                                                description:    String
                                                type:           String
                                                other_params:   Dictionary
                                            }]

                                    output: Dictionary
                                            This is the output as defined in the configuration - the
                                            primary output will always be named 'primary'
                                            {
                                                name:             String
                                                publish_template: template
                                                tank_type:        String
                                            }
                                }

        :param work_template:   template
                                This is the template defined in the config that
                                represents the current work file

        :param comment:         String
                                The comment provided for the publish

        :param thumbnail:       Path string
                                The default thumbnail provided for the publish

        :param sg_task:         Dictionary (shotgun entity description)
                                The shotgun task to use for the publish

        :param progress_cb:     Function
                                A progress callback to log progress during pre-publish.  Call:

                                    progress_cb(percentage, msg)

                                to report progress to the UI

        :returns:               Path String
                                Hook should return the path of the primary publish so that it
                                can be passed as a dependency to all secondary publishes

        :raises:                Hook should raise a TankError if publish of the
                                primary task fails
        """
        # get the engine name from the parent object (app/engine/etc.)
        engine_name = self.parent.engine.name
        

        # depending on engine:
        if engine_name == "tk-maya":
            return self._do_maya_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        elif engine_name == "tk-motionbuilder":
            return self._do_motionbuilder_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        elif engine_name == "tk-nuke":
            return self._do_nuke_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        elif engine_name == "tk-3dsmax":
            return self._do_3dsmax_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        elif engine_name == "tk-3dsmaxplus":
            return self._do_3dsmaxplus_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        elif engine_name == "tk-hiero":
            return self._do_hiero_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        elif engine_name == "tk-houdini":
            return self._do_houdini_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        elif engine_name == "tk-softimage":
            return self._do_softimage_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        elif engine_name == "tk-photoshop":
            return self._do_photoshop_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        elif engine_name == "tk-mari":
            return self._do_mari_publish(task, work_template, comment, thumbnail_path, sg_task, progress_cb)
        else:
            raise TankError(
                "Unable to perform publish for unhandled engine %s" % engine_name)

    def _do_maya_publish(self, task, work_template, comment, thumbnail_path, sg_task, progress_cb):
        """
        Publish the main Maya scene

        :param task:            The primary task to publish
        :param work_template:   The primary work template to use
        :param comment:         The publish description/comment
        :param thumbnail_path:  The path to the thumbnail to associate with the published file
        :param sg_task:         The Shotgun task that this publish should be associated with
        :param progress_cb:     A callback to use when reporting any progress
                                to the UI
        :returns:               The path to the file that has been published
        """
        self.parent.log_debug(self.parent)
        self.infoNodeLib = InfoNodeLib(self.parent)
        import maya.cmds as cmds

        progress_cb(0.0, "Finding scene dependencies", task)
        dependencies = self._maya_find_additional_scene_dependencies()

        # get scene path
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))

        if not work_template.validate(scene_path):
            raise TankError(
                "File '%s' is not a valid work path, unable to publish!" % scene_path)

        # use templates to convert to publish path:
        output = task["output"]
        for out in output:
            self.parent.log_debug("%s : %s" % (out, output[out]))


        fields = work_template.get_fields(scene_path)
        fields["TankType"] = output["tank_type"]
        if "LGT" in fields['cs_task_name']:
            publish_path = self._do_maya_lighting_publish(task, work_template, fields, dependencies, scene_path, comment, thumbnail_path, sg_task, progress_cb)
        else:
            publish_path = self._do_maya_generic_publish(task, work_template, fields, dependencies, scene_path, comment, thumbnail_path, sg_task, progress_cb)

        progress_cb(100)

        return publish_path

    def _do_maya_generic_publish(self,task, work_template, fields, dependencies, scene_path, comment, thumbnail_path, sg_task, progress_cb):
        import maya.cmds as cmds
        output = task["output"]
        publish_template = output["publish_template"]
        publish_path = ""

        #---------------------------------------------
        # STEP 1 :  Prep up path and Save the current scene
        #---------------------------------------------
        next_version = self._get_next_work_file_version(work_template, fields)
        fields['cs_publi_flag'] = "publi"
        fields["version"] = next_version

        publish_path = publish_template.apply_fields(fields)

        if os.path.exists(publish_path):
                raise TankError(
                    "The published file named '%s' already exists!" % publish_path)

        new_scene_path = work_template.apply_fields(fields)
        progress_cb(20.0, "Saving the scene")
        self.parent.log_debug("Saving the scene...")
        cmds.file(rename=new_scene_path)
        cmds.file(save=True, force=True)
        old_path = scene_path
        scene_path = new_scene_path

        #---------------------------------------------
        # STEP 2 :  Clean up processes
        #---------------------------------------------
        self._do_maya_scene_cleanup(scene_path,old_path,work_template,fields)

        #---------------------------------------------
        # STEP 3 :  Save As published file
        #---------------------------------------------
        progress_cb(60.0, "Saving Publish file")
        try:
            publish_folder = os.path.dirname(publish_path)
            self.parent.ensure_folder_exists(publish_folder)
            self.parent.log_debug(
                "Saving %s --> %s..." % (scene_path, publish_path))
            cmds.file(rename=publish_path)
            cmds.file(save=True, force=True)
            # self.parent.copy_file(scene_path, publish_path, task)
        except Exception, e:
            raise TankError(
                "Failed to save file from to %s - %s" % (publish_path, e))
        #---------------------------------------------
        # STEP 4 : hard_link last version to root folder
        #---------------------------------------------
        self._hard_link_last_publish(
            progress_cb, publish_path,  task)

        #---------------------------------------------
        # STEP 5 : get publish name
        #---------------------------------------------
        publish_name = self._get_publish_name(
            publish_path, publish_template, fields)

        #---------------------------------------------
        # STEP 6 : register the publish
        #---------------------------------------------
        progress_cb(75.0, "Registering the publish")
        self._register_publish(publish_path,
                               publish_name,
                               sg_task,
                               fields["version"],
                               output["tank_type"],
                               comment,
                               thumbnail_path,
                               dependencies)
        return publish_path
    
    def _do_maya_lighting_publish(self,task, work_template, fields, dependencies, scene_path, comment, thumbnail_path, sg_task, progress_cb):
        import maya.cmds as cmds
        output = task["output"]
        publish_template = self.parent.tank.templates['maya_shot_publish_lgt']
        publish_path = ""
        #---------------------------------------------
        # STEP 1 :  Prep up path and Save the current scene
        #---------------------------------------------
        fields['cs_publi_flag'] = "publi"

        publish_path = publish_template.apply_fields(fields)

        if os.path.exists(publish_path):
                raise TankError(
                    "The published file named '%s' already exists!" % publish_path)

        new_scene_path = work_template.apply_fields(fields)
        progress_cb(20.0, "Saving the scene")
        self.parent.log_debug("Saving the scene...")
        cmds.file(rename=new_scene_path)
        cmds.file(save=True, force=True)
        old_path = scene_path
        scene_path = new_scene_path

        #---------------------------------------------
        # STEP 2 :  Clean up processes
        #---------------------------------------------
        self._do_maya_scene_cleanup(scene_path,old_path,work_template,fields)

        #---------------------------------------------
        # STEP 3 :  Save As published file
        #---------------------------------------------
        progress_cb(60.0, "Saving Publish file")
        try:
            publish_folder = os.path.dirname(publish_path)
            self.parent.ensure_folder_exists(publish_folder)
            self.parent.log_debug(
                "Saving %s --> %s..." % (scene_path, publish_path))
            cmds.file(rename=publish_path)
            cmds.file(save=True, force=True)
            # self.parent.copy_file(scene_path, publish_path, task)
        except Exception, e:
            raise TankError(
                "Failed to save file from to %s - %s" % (publish_path, e))


        #---------------------------------------------
        # STEP 5 : get publish name
        #---------------------------------------------
        publish_name = self._get_publish_name(
            publish_path, publish_template, fields)

        #---------------------------------------------
        # STEP 6 : register the publish
        #---------------------------------------------
        progress_cb(75.0, "Registering the publish")
        self._register_publish(publish_path,
                               publish_name,
                               sg_task,
                               fields["version"],
                               output["tank_type"],
                               comment,
                               thumbnail_path,
                               dependencies)

        return publish_path

    def _maya_find_additional_scene_dependencies(self):
        """
        Find additional dependencies from the scene
        """
        import maya.cmds as cmds

        # default implementation looks for references and
        # textures (file nodes) and returns any paths that
        # match a template defined in the configuration
        ref_paths = set()

        # first let's look at maya references
        ref_nodes = cmds.ls(references=True)
        for ref_node in ref_nodes:
            # get the path:
            ref_path = cmds.referenceQuery(ref_node, filename=True)
            # make it platform dependent
            # (maya uses C:/style/paths)
            ref_path = ref_path.replace("/", os.path.sep)
            if ref_path:
                ref_paths.add(ref_path)

        # now look at file texture nodes
        for file_node in cmds.ls(l=True, type="file"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(file_node, isNodeReferenced=True):
                # this is embedded in another reference, so don't include it in the
                # breakdown
                continue

            # get path and make it platform dependent
            # (maya uses C:/style/paths)
            texture_path = cmds.getAttr(
                "%s.fileTextureName" % file_node).replace("/", os.path.sep)
            if texture_path:
                ref_paths.add(texture_path)

        # now, for each reference found, build a list of the ones
        # that resolve against a template:
        dependency_paths = []
        for ref_path in ref_paths:
            # see if there is a template that is valid for this path:
            for template in self.parent.tank.templates.values():
                if template.validate(ref_path):
                    dependency_paths.append(ref_path)
                    break

        return dependency_paths

    def _do_nuke_publish(self, task, work_template, comment, thumbnail_path, sg_task, progress_cb):
        """
        Publish the main Nuke script

        :param task:            The primary task to publish
        :param work_template:   The primary work template to use
        :param comment:         The publish description/comment
        :param thumbnail_path:  The path to the thumbnail to associate with the published file
        :param sg_task:         The Shotgun task that this publish should be associated with
        :param progress_cb:     A callback to use when reporting any progress
                                to the UI
        :returns:               The path to the file that has been published        
        """
        import nuke
        
        progress_cb(0.0, "Finding dependencies", task)
        dependencies = self._nuke_find_script_dependencies()
        
        # get scene path
        script_path = nuke.root().name().replace("/", os.path.sep)
        if script_path == "Root":
            script_path = ""
        script_path = os.path.abspath(script_path)
        
        if not work_template.validate(script_path):
            raise TankError("File '%s' is not a valid work path, unable to publish!" % script_path)
        
        # use templates to convert to publish path:
        output = task["output"]
        fields = work_template.get_fields(script_path)
        fields["TankType"] = output["tank_type"]
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)
        
        if os.path.exists(publish_path):
            raise TankError("The published file named '%s' already exists!" % publish_path)
        
        # save the scene:
        progress_cb(25.0, "Saving the script")
        self.parent.log_debug("Saving the Script...")
        nuke.scriptSave()
        
        # copy the file:
        progress_cb(50.0, "Copying the file")
        try:
            publish_folder = os.path.dirname(publish_path)
            self.parent.ensure_folder_exists(publish_folder)
            self.parent.log_debug("Copying %s --> %s..." % (script_path, publish_path))
            self.parent.copy_file(script_path, publish_path, task)
        except Exception, e:
            raise TankError("Failed to copy file from %s to %s - %s" % (script_path, publish_path, e))

        # work out name for publish:
        publish_name = self._get_publish_name(publish_path, publish_template, fields)

        # finally, register the publish:
        progress_cb(75.0, "Registering the publish")
        self._register_publish(publish_path, 
                               publish_name, 
                               sg_task, 
                               fields["version"], 
                               output["tank_type"],
                               comment,
                               thumbnail_path, 
                               dependencies)
        
        progress_cb(100)
        
        return publish_path
        

    def _nuke_find_script_dependencies(self):
        """
        Find all dependencies for the current nuke script
        """
        import nuke

        # figure out all the inputs to the scene and pass them as dependency
        # candidates
        dependency_paths = []
        for read_node in nuke.allNodes("Read"):
            # make sure we have a file path and normalize it
            # file knobs set to "" in Python will evaluate to None. This is different than
            # if you set file to an empty string in the UI, which will evaluate
            # to ""!
            file_name = read_node.knob("file").evaluate()
            if not file_name:
                continue
            file_name = file_name.replace('/', os.path.sep)

            # validate against all our templates
            for template in self.parent.tank.templates.values():
                if template.validate(file_name):
                    fields = template.get_fields(file_name)
                    # translate into a form that represents the general
                    # tank write node path.
                    fields["SEQ"] = "FORMAT: %d"
                    fields["eye"] = "%V"
                    dependency_paths.append(template.apply_fields(fields))
                    break

        return dependency_paths



    def _do_photoshop_publish(self, task, work_template, comment, thumbnail_path, sg_task, progress_cb):
        """
        Publish the main Photoshop scene

        :param task:            The primary task to publish
        :param work_template:   The primary work template to use
        :param comment:         The publish description/comment
        :param thumbnail_path:  The path to the thumbnail to associate with the published file
        :param sg_task:         The Shotgun task that this publish should be associated with
        :param progress_cb:     A callback to use when reporting any progress
                                to the UI
        :returns:               The path to the file that has been published
        """
        import photoshop

        doc = photoshop.app.activeDocument
        if doc is None:
            raise TankError("There is no currently active document!")

        # get scene path
        scene_path = doc.fullName.nativePath

        if not work_template.validate(scene_path):
            raise TankError(
                "File '%s' is not a valid work path, unable to publish!" % scene_path)

        # use templates to convert to publish path:
        output = task["output"]
        fields = work_template.get_fields(scene_path)
        fields["TankType"] = output["tank_type"]
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)

        if os.path.exists(publish_path):
            raise TankError(
                "The published file named '%s' already exists!" % publish_path)

        # save the scene:
        progress_cb(0.0, "Saving the scene")
        self.parent.log_debug("Saving the scene...")
        doc.save()

        # copy the file:
        progress_cb(25.0, "Copying the file")
        try:
            publish_folder = os.path.dirname(publish_path)
            self.parent.ensure_folder_exists(publish_folder)
            self.parent.log_debug(
                "Copying %s --> %s..." % (scene_path, publish_path))
            self.parent.copy_file(scene_path, publish_path, task)
        except Exception, e:
            raise TankError(
                "Failed to copy file from %s to %s - %s" % (scene_path, publish_path, e))

        # work out publish name:
        publish_name = self._get_publish_name(
            publish_path, publish_template, fields)

        # finally, register the publish:
        progress_cb(50.0, "Registering the publish")
        tank_publish = self._register_publish(publish_path,
                                              publish_name,
                                              sg_task,
                                              fields["version"],
                                              output["tank_type"],
                                              comment,
                                              thumbnail_path,
                                              dependency_paths=[])

        #######################################################################
        # create a version!

        jpg_pub_path = os.path.join(
            tempfile.gettempdir(), "%s_sgtk.jpg" % uuid.uuid4().hex)

        thumbnail_file = photoshop.RemoteObject(
            'flash.filesystem::File', jpg_pub_path)
        jpeg_options = photoshop.RemoteObject(
            'com.adobe.photoshop::JPEGSaveOptions')
        jpeg_options.quality = 12

        # save as a copy
        photoshop.app.activeDocument.saveAs(thumbnail_file, jpeg_options, True)

        # then register version
        progress_cb(60.0, "Creating Version...")
        ctx = self.parent.context
        data = {
            "user": ctx.user,
            "description": comment,
            "sg_first_frame": 1,
            "frame_count": 1,
            "frame_range": "1-1",
            "sg_last_frame": 1,
            "entity": ctx.entity,
            "sg_path_to_frames": publish_path,
            "project": ctx.project,
            "sg_task": sg_task,
            "code": tank_publish["code"],
            "created_by": ctx.user,
        }

        if tank.util.get_published_file_entity_type(self.parent.tank) == "PublishedFile":
            data["published_files"] = [tank_publish]
        else:  # == "TankPublishedFile"
            data["tank_published_file"] = tank_publish

        version = self.parent.shotgun.create("Version", data)

        # upload jpeg
        progress_cb(70.0, "Uploading to Shotgun...")
        self.parent.shotgun.upload(
            "Version", version['id'], jpg_pub_path, "sg_uploaded_movie")

        try:
            os.remove(jpg_pub_path)
        except:
            pass

        progress_cb(100)

        return publish_path

    def _get_publish_name(self, path, template, fields=None):
        """
        Return the 'name' to be used for the file - if possible
        this will return a 'versionless' name
        """
        # first, extract the fields from the path using the template:
        fields = fields.copy() if fields else template.get_fields(path)
        if "name" in fields and fields["name"]:
            # well, that was easy!
            name = fields["name"]
        else:
            # find out if version is used in the file name:
            template_name, _ = os.path.splitext(
                os.path.basename(template.definition))
            version_in_name = "{version}" in template_name

            # extract the file name from the path:
            name, _ = os.path.splitext(os.path.basename(path))
            delims_str = "_-. "
            if version_in_name:
                # looks like version is part of the file name so we
                # need to isolate it so that we can remove it safely.
                # First, find a dummy version whose string representation
                # doesn't exist in the name string
                version_key = template.keys["version"]
                dummy_version = 9876
                while True:
                    test_str = version_key.str_from_value(dummy_version)
                    if test_str not in name:
                        break
                    dummy_version += 1

                # now use this dummy version and rebuild the path
                fields["version"] = dummy_version
                path = template.apply_fields(fields)
                name, _ = os.path.splitext(os.path.basename(path))

                # we can now locate the version in the name and remove it
                dummy_version_str = version_key.str_from_value(dummy_version)

                v_pos = name.find(dummy_version_str)
                # remove any preceeding 'v'
                pre_v_str = name[:v_pos].rstrip("v")
                post_v_str = name[v_pos + len(dummy_version_str):]

                if (pre_v_str and post_v_str
                        and pre_v_str[-1] in delims_str
                        and post_v_str[0] in delims_str):
                    # only want one delimiter - strip the second one:
                    post_v_str = post_v_str.lstrip(delims_str)

                versionless_name = pre_v_str + post_v_str
                versionless_name = versionless_name.strip(delims_str)

                if versionless_name:
                    # great - lets use this!
                    name = versionless_name
                else:
                    # likely that version is only thing in the name so
                    # instead, replace the dummy version with #'s:
                    zero_version_str = version_key.str_from_value(0)
                    new_version_str = "#" * len(zero_version_str)
                    name = name.replace(dummy_version_str, new_version_str)

        return name

    def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, dependency_paths):
        """
        Helper method to register publish using the
        specified publish info.
        """
        # construct args:
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": path,
            "name": name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": dependency_paths,
            "published_file_type": tank_type,
        }

        self.parent.log_debug("Register publish in shotgun: %s" % str(args))

        # register publish;
        sg_data = tank.util.register_publish(**args)

        return sg_data

    def _hard_link_last_publish(self, progress_cb, publish_file_path, task):
        import re
        # hardlink file to root folder
        publish_folder, publish_file_name = os.path.split(publish_file_path)
        root_folder = os.path.dirname(publish_folder)
        self.parent.log_debug("root: %s" % root_folder)
        pub_link_name = root_folder + os.sep + \
            re.sub(r"-v\d{3}", "", publish_file_name)
        pub_link_name = pub_link_name.replace("-publi","")
        self.parent.log_debug("pub_link_name: %s" % pub_link_name)
        try:
            if os.path.exists(pub_link_name):
                os.remove(pub_link_name)
            os.link(publish_file_path, pub_link_name)
        except Exception, e:
            raise TankError(str(e))

    def _get_next_work_file_version(self, work_template, fields):
        """
        Find the next available version for the specified work_file
        """
        # self.parent.log_debug("work_template: %s"%work_template)
        # self.parent.log_debug("fields: %s"%fields)
        existing_versions = self.parent.tank.paths_from_template(work_template, fields, ["version","cs_user_name","cs_publi_flag"])
        # self.parent.log_debug("existing_versions: %s" % existing_versions)

        version_numbers = [work_template.get_fields(v).get("version") for v in existing_versions]
        self.parent.log_debug("existing_versions: %s" % version_numbers)

        curr_v_no = fields["version"]
        max_v_no = max(version_numbers)
        return max(curr_v_no, max_v_no) + 1

    def _do_maya_scene_cleanup(self,scene_path,old_path,work_template,fields):
        """
        @summary: do maya scene clean up before publish
        """
        self.parent.log_debug("#** Starting clean up **#")
        #Find which step we are in and execute according cleanups
        if "cs_task_name" in fields:
            short_code = fields['cs_task_name']
            self.parent.log_debug("#== Task: %s"%short_code)
            #dispatch clean up
            #MODELING
            if "MO" in short_code:
                self.parent.log_debug("#=> Starting modeling Clean Up")
                self._do_maya_modeling_cleanup(scene_path,old_path,work_template,fields)
            elif "SE" in short_code:
                self.parent.log_debug("#=> Starting setup Clean Up")
                self._do_maya_setup_cleanup(scene_path,old_path,work_template,fields)
            elif "CO" in short_code:
                self.parent.log_debug("#=> Starting color Clean Up")
                self._do_maya_color_cleanup(scene_path,old_path,work_template,fields)
            elif "LO" in short_code:
                self.parent.log_debug("#=> Starting layout Clean Up")
                self._do_maya_layout_cleanup(scene_path,old_path,work_template,fields)
            elif "AN" in short_code:
                self.parent.log_debug("#=> Starting animation Clean Up")
                self._do_maya_animation_cleanup(scene_path,old_path,work_template,fields)
            elif "LGT" in short_code:
                self.parent.log_debug("#=> Starting lighting Clean Up")
                self._do_maya_lighting_cleanup(scene_path,old_path,work_template,fields)
            elif "TRK" in short_code:
                self.parent.log_debug("#=> Starting tracking Clean Up")
                self._do_maya_tracking_cleanup(scene_path,old_path,work_template,fields)
                
    def _do_maya_modeling_cleanup(self,scene_path,old_path,work_template,fields):
        # ASSET CLEANUP
        if "Asset" in fields.keys():
            self._do_maya_check_info_node(scene_path,old_path)
            self._do_maya_aovs_cleanup()
            self._do_maya_delete_group_cleanup()
            self._do_maya_shaders_cleanup()

    def _do_maya_color_cleanup(self,scene_path,old_path,work_template,fields):
        # ASSET CLEANUP
        if "Asset" in fields.keys():
            self._do_maya_check_info_node(scene_path,old_path)
            self._do_maya_delete_group_cleanup()

    def _do_maya_setup_cleanup(self,scene_path,old_path,work_template,fields):
        # ASSET CLEANUP
        if "Asset" in fields.keys():
            self._do_maya_check_info_node(scene_path,old_path)
            self._do_maya_delete_group_cleanup()

    def _do_maya_layout_cleanup(self,scene_path,old_path,work_template,fields):
        # SHOT CLEANUP
        if "Shot" in fields.keys():
            self._do_maya_check_info_node(scene_path,old_path)
            self._do_maya_delete_group_cleanup()

    def _do_maya_tracking_cleanup(self,scene_path,old_path,work_template,fields):
        # SHOT CLEANUP
        if "Shot" in fields.keys():
            self._do_maya_check_info_node(scene_path,old_path)
            self._do_maya_delete_group_cleanup()

    def _do_maya_animation_cleanup(self,scene_path,old_path,work_template,fields):
        # SHOT CLEANUP
        if "Shot" in fields.keys():
            self._do_maya_check_info_node(scene_path,old_path)
            self._do_maya_delete_group_cleanup()

    def _do_maya_lighting_cleanup(self,scene_path,old_path,work_template,fields):
        # SHOT CLEANUP
        if "Shot" in fields.keys():
            self._do_maya_check_info_node(scene_path,old_path)
            self._do_maya_delete_group_cleanup()

    def _do_maya_aovs_cleanup(self):
        import maya.cmds as cmds
        try:
            # AOVS CLEANUP
            self.parent.log_debug("  +---> Cleaning AOVs")

            # Active AOVs CLEANUP
            activeAOVS = cmds.ls(et='aiAOV')
            for AOV in activeAOVS:
                if not AOV.count('default'):
                    cmds.delete(AOV)
            self.parent.log_debug("  | > Cleanup of active AOVs ok !")

            # Active AOVs Filters CLEANUP
            activeFilters = cmds.ls(et='aiAOVFilter')
            for Filter in activeFilters:
                if not Filter.count('default'):
                    cmds.delete(Filter)
            self.parent.log_debug("  | > Cleanup of active AOV Filters ok !")

            # Active AOVs Drivers CLEANUP
            activeDrivers = cmds.ls(et='aiAOVDriver')
            for Driver in activeDrivers:
                if not Driver.count('default'):
                    cmds.delete(Driver)
            self.parent.log_debug("  | > Cleanup of active AOV Drivers ok !")

            self.parent.log_debug("  +---> Cleaning AOVs Complete  !")

        except Exception, e:
            self.parent.log_debug("Failed cleaning up AOVs: %s"%e)


        self.parent.log_debug("")

    def _do_maya_delete_group_cleanup(self):
        import maya.cmds as cmds
        try:
            # To_delete Group CLEANUP
            self.parent.log_debug("  +---> Cleaning To_delete Group")
            nodeToDelete = 'To_delete'
            if cmds.objExists( nodeToDelete ):
                cmds.lockNode(nodeToDelete, l=0  )
                self.infoNodeLib.maya_delete_if_not_referenced(nodeToDelete)
            self.parent.log_debug("  +---> Cleanup of To_delete Group ok  !")

        except Exception, e:
            self.parent.log_debug("  | > !!! Failed cleaning up To_delete Group: %s"%e)
        self.parent.log_debug("")

    def _do_maya_shaders_cleanup(self):
        import maya.cmds as cmds
        try:
             # Shaders CLEANUP
            self.parent.log_debug("  +---> Cleaning Shaders")
            allMat = cmds.ls( mat=True, tex=True)
            for el in allMat:
                if cmds.objExists(el):
                    allConn = cmds.listConnections(el, scn=True)
                    for con in allConn:
                        if cmds.objExists(con):
                            cmds.delete(con)
                    self.parent.log_debug("  | > Cleanup of \"%s\" ok !"%el)
                    cmds.delete(el)
            nodeName = 'lambert1'
            attrs = cmds.listAttr(nodeName,scalar=True, settable=True)

            for attr in attrs:
                # print attr
                if '.' in attr:
                    continue
                value = cmds.attributeQuery( attr, node=nodeName, listDefault=True)
                str= nodeName + '.' + attr
                if cmds.attributeQuery(attr,node=nodeName,exists=True):
                    cmds.setAttr(str,value[0])
            allUtility=cmds.ls( typ=('place2dTexture','place3dTexture','projection','blendColors','bump2d','bump3d','heightField','curveInfo','gammaCorrect','hsvToRgb','luminance','samplerInfo','stencil','surfaceInfo','imagePlane'))
            for u in allUtility:
                if cmds.objExists(u):
                    self.parent.log_debug("  | > Cleanup of \"%s\" ok !"%u)
                    cmds.delete(u)
            allMeshes = cmds.ls( type='mesh')
            # DShader=cmds.shadingNode("lambert",asShader=True)
            shading_group= cmds.sets(renderable=True,noSurfaceShader=True,empty=True)
            cmds.connectAttr('%s.outColor' %nodeName ,'%s.surfaceShader' %shading_group)
            cmds.sets(allMeshes, e=True, forceElement=shading_group)
            self.parent.log_debug("  | > Relinked all meshed to default shaders ok !"%u)

            self.parent.log_debug("  +---> Cleanup of Shaders ok  !")
        except Exception, e:
            self.parent.log_debug("  | > !!! Failed cleaning up Shaders: %s"%e)
        self.parent.log_debug("")

    def _do_maya_check_info_node(self,scene_path,old_path):
        import maya.cmds as cmds
        context = self.parent.context
        if cmds.objExists( "mikInfo" ) :
            self.parent.log_debug("Found mikinfo node .. ")
        else:
            self.parent.log_debug("Creating mikinfo node .. ")
            self.infoNodeLib.maya_create_mikinfo_node(context)
        self.infoNodeLib.maya_update_mikinfo_node(context,old_path,scene_path)
        self.infoNodeLib.maya_check_info_node()