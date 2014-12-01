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
import sys

import tank
from tank import Hook
from tank import TankError

class PostPublishHook(Hook):
    """
    Single hook that implements post-publish functionality
    """
    def execute(self, work_template, primary_task, secondary_tasks, progress_cb, **kwargs):
        """
        Main hook entry point

        :param work_template:   template
                                This is the template defined in the config that
                                represents the current work file

        :param primary_task:    The primary task that was published by the primary publish hook.  Passed
                                in here for reference.

        :param secondary_tasks: The list of secondary taskd that were published by the secondary
                                publish hook.  Passed in here for reference.

        :param progress_cb:     Function
                                A progress callback to log progress during pre-publish.  Call:

                                    progress_cb(percentage, msg)

                                to report progress to the UI

        :returns:               None
        :raises:                Raise a TankError to notify the user of a problem
        """
        # get the engine name from the parent object (app/engine/etc.)
        engine_name = self.parent.engine.name

        # depending on engine:
        if engine_name == "tk-maya":
            self._do_maya_post_publish(work_template, progress_cb)
        elif engine_name == "tk-motionbuilder":
            self._do_motionbuilder_post_publish(work_template, progress_cb)
        elif engine_name == "tk-nuke":
            self._do_nuke_post_publish(work_template, progress_cb)
        elif engine_name == "tk-3dsmax":
            self._do_3dsmax_post_publish(work_template, progress_cb)
        elif engine_name == "tk-3dsmaxplus":
            self._do_3dsmaxplus_post_publish(work_template, progress_cb)
        elif engine_name == "tk-hiero":
            self._do_hiero_post_publish(work_template, progress_cb)
        elif engine_name == "tk-houdini":
            self._do_houdini_post_publish(work_template, progress_cb)
        elif engine_name == "tk-softimage":
            self._do_softimage_post_publish(work_template, progress_cb)
        elif engine_name == "tk-photoshop":
            self._do_photoshop_post_publish(work_template, progress_cb)
        elif engine_name == "tk-mari":
            self._do_mari_post_publish(work_template, progress_cb)
        else:
            raise TankError("Unable to perform post publish for unhandled engine %s" % engine_name)

    def _do_maya_post_publish(self, work_template, progress_cb):
        """
        Do any Maya post-publish work

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        import maya.cmds as cmds

        progress_cb(0, "Versioning up the scene file")

        # get the current scene path:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        to_open = self._get_current_work_file_version(scene_path)
        # increment version and construct new file name:
        progress_cb(25, "Finding Scene to reopen")

        # log info
        self.parent.log_debug("Opening the scene file %s..." % ( to_open))

        # open  the file
        try:
            progress_cb(50, "Opening the scene file")
            cmds.file(to_open,open=True, force=True)
        except Exception, e:
            raise TankError("Could not open the original wip file %s, starting a new scene."%to_open)
            cmds.file(new=True,force=True)

        progress_cb(100)

    def _do_motionbuilder_post_publish(self, work_template, progress_cb):
        """
        Do any Motion Builder post-publish work

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        from pyfbsdk import FBApplication

        mb_app = FBApplication()

        progress_cb(0, "Versioning up the script")

        # get the current script path:
        original_path = mb_app.FBXFileName
        script_path = os.path.abspath(original_path)

        # increment version and construct new name:
        progress_cb(25, "Finding next version number")
        fields = work_template.get_fields(script_path)
        next_version = self._get_next_work_file_version(work_template, fields)
        fields["version"] = next_version
        new_path = work_template.apply_fields(fields)

        # log info
        self.parent.log_debug("Version up work file %s --> %s..." % (script_path, new_path))

        # save the script:
        progress_cb(75, "Saving the scene file")
        mb_app.FileSave(new_path)

        progress_cb(100)

    def _do_3dsmax_post_publish(self, work_template, progress_cb):
        """
        Do any 3ds Max post-publish work

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        from Py3dsMax import mxs

        progress_cb(0, "Versioning up the scene file")

        # get scene path
        scene_path = os.path.abspath(os.path.join(mxs.maxFilePath, mxs.maxFileName))

        # increment version and construct new file name:
        progress_cb(25, "Finding next version number")
        fields = work_template.get_fields(scene_path)
        next_version = self._get_next_work_file_version(work_template, fields)
        fields["version"] = next_version
        new_scene_path = work_template.apply_fields(fields)

        # log info
        self.parent.log_debug("Version up work file %s --> %s..." % (scene_path, new_scene_path))

        # rename and save the file
        progress_cb(50, "Saving the scene file")
        mxs.saveMaxFile(new_scene_path)

        progress_cb(100)

    def _do_3dsmaxplus_post_publish(self, work_template, progress_cb):
        """
        Do any 3ds Max post-publish work

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        import MaxPlus

        progress_cb(0, "Versioning up the scene file")

        # get scene path
        scene_path = MaxPlus.FileManager.GetFileNameAndPath()

        # increment version and construct new file name:
        progress_cb(25, "Finding next version number")
        fields = work_template.get_fields(scene_path)
        next_version = self._get_next_work_file_version(work_template, fields)
        fields["version"] = next_version
        new_scene_path = work_template.apply_fields(fields)

        # log info
        self.parent.log_debug("Version up work file %s --> %s..." % (scene_path, new_scene_path))

        # rename and save the file
        progress_cb(50, "Saving the scene file")
        MaxPlus.FileManager.Save(new_scene_path)

        progress_cb(100)

    def _do_hiero_post_publish(self, work_template, progress_cb):
        """
        Do any Hiero post-publish work

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        import hiero.core

        progress_cb(0, "Versioning up the scene file")

        # first find which the current project is. Hiero is a multi project
        # environment so we can ask the engine which project was clicked in order
        # to launch this publish.
        selection = self.parent.engine.get_menu_selection()

        # these values should in theory already be validated, but just in case...
        if len(selection) != 1:
            raise TankError("Please select a single Project!")
        if not isinstance(selection[0] , hiero.core.Bin):
            raise Exception("Please select a Hiero Project!")
        project = selection[0].project()
        if project is None:
            # apparently bins can be without projects (child bins I think)
            raise TankError("Please select a Hiero Project!")

        # get the current scene path:
        scene_path = os.path.abspath(project.path().replace("/", os.path.sep))

        # increment version and construct new file name:
        progress_cb(25, "Finding next version number")
        fields = work_template.get_fields(scene_path)
        next_version = self._get_next_work_file_version(work_template, fields)
        fields["version"] = next_version
        new_scene_path = work_template.apply_fields(fields)

        # log info
        self.parent.log_debug("Version up work file %s --> %s..." % (scene_path, new_scene_path))

        # rename and save the file
        progress_cb(50, "Saving the scene file")
        project.saveAs(new_scene_path.replace(os.path.sep, "/"))

        progress_cb(100)


    def _do_nuke_post_publish(self, work_template, progress_cb):
        """
        Do any nuke post-publish work

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        import nuke

        progress_cb(0, "")

        # get the current script path:
        scene_path = nuke.root()["name"].getValue()
        to_open = self._get_current_work_file_version(scene_path)

        # increment version and construct new name:
        progress_cb(25, "Finding Scene to reopen")

        # log info
        self.parent.log_debug("Opening the scene file %s..." % ( to_open))

        # open  the file
        try:
            progress_cb(50, "Opening the scene file")
            nuke.scriptOpen(to_open)
        except Exception, e:
            raise TankError("Could not open the original wip file %s, starting a new scene."%to_open)
            nuke.scriptNew()

        progress_cb(100)

    def _do_houdini_post_publish(self, work_template, progress_cb):
        """
        Do any nuke post-publish work

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        import hou

        progress_cb(0, "Versioning up the script")

        # get the current script path:
        original_path = hou.hipFile.name()
        script_path = os.path.abspath(original_path)

        # increment version and construct new name:
        progress_cb(25, "Finding next version number")
        fields = work_template.get_fields(script_path)
        next_version = self._get_next_work_file_version(work_template, fields)
        fields["version"] = next_version
        new_path = work_template.apply_fields(fields)

        # log info
        self.parent.log_debug("Version up work file %s --> %s..." % (script_path, new_path))

        # save the script:
        progress_cb(75, "Saving the scene file")
        if sys.platform == 'win32':
            new_path = new_path.replace(os.path.sep, '/')
        hou.hipFile.save(new_path)

        progress_cb(100)

    def _do_softimage_post_publish(self, work_template, progress_cb):
        """
        Do any Softimage post-publish work

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        import win32com
        from win32com.client import Dispatch, constants
        from pywintypes import com_error
        Application = Dispatch("XSI.Application").Application

        progress_cb(0, "Versioning up the scene file")

        # get the current scene path:
        scene_path = os.path.abspath(Application.ActiveProject.ActiveScene.filename.value)

        # increment version and construct new file name:
        progress_cb(25, "Finding next version number")
        fields = work_template.get_fields(scene_path)
        next_version = self._get_next_work_file_version(work_template, fields)
        fields["version"] = next_version
        new_scene_path = work_template.apply_fields(fields)

        # log info
        self.parent.log_debug("Version up work file %s --> %s..." % (scene_path, new_scene_path))

        # rename and save the file
        progress_cb(50, "Saving the scene file")
        Application.SaveSceneAs(new_scene_path, False)

        progress_cb(100)

    def _do_photoshop_post_publish(self, work_template, progress_cb):
        """
        Do any Photoshop post-publish work

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        import photoshop

        progress_cb(0, "Versioning up the scene file")

        # get the current scene path:
        doc = photoshop.app.activeDocument
        if doc is None:
            raise TankError("There is no currently active document!")
        scene_path = doc.fullName.nativePath

        # increment version and construct new file name:
        progress_cb(25, "Finding next version number")
        fields = work_template.get_fields(scene_path)
        next_version = self._get_next_work_file_version(work_template, fields)
        fields["version"] = next_version
        new_scene_path = work_template.apply_fields(fields)

        # log info
        self.parent.log_debug("Version up work file %s --> %s..." % (scene_path, new_scene_path))

        # rename and save the file
        progress_cb(50, "Saving the scene file")
        new_file_name = photoshop.RemoteObject('flash.filesystem::File', new_scene_path)
        # no options and do not save as a copy
        # http://cssdk.host.adobe.com/sdk/1.5/docs/WebHelp/references/csawlib/com/adobe/photoshop/Document.html#saveAs()
        doc.saveAs(new_file_name, None, False)

        progress_cb(100)

    def _do_mari_post_publish(self, work_template, progress_cb):
        """
        Mari specific post-publish

        :param work_template:   The primary work template used for the publish
        :param progress_cb:     Callback to be used when reporting progress
        """
        # nothing to do for Mari post-publish
        pass


    def _get_current_work_file_version(self, scene_path):
        """
        Find the next available vesion for the specified work_file
        """
        self.parent.log_debug("current_file:%s"%scene_path)
        user = tank.util.get_current_user(self.parent.tank)
        path_to_wip = scene_path.replace("refOrig%s"%os.sep,"wip%s%s%s"%(os.sep,user['login'],os.sep))
        self.parent.log_debug("path_to_wip:%s"%path_to_wip)
        return path_to_wip








