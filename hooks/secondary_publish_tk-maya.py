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
import shutil
import maya.cmds as cmds
import maya.mel as mel

import tank
from tank import Hook
from tank import TankError
import sys
import re

LINUX_PATH = "/s/apps/common/python/luigi/infonodelib"
WINDOWS_PATH = "V:\\apps\\common\\python\\luigi\\infonodelib"
info_lib_path = {"linux2": LINUX_PATH,
              "win32":  WINDOWS_PATH,
              "darwin": "" }

sys.path.append(info_lib_path[sys.platform])

from infonodelib import InfoNodeLib
class PublishHook(Hook):
    """
    Single hook that implements publish functionality for secondary tasks
    """    
    def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_task, primary_publish_path, progress_cb, **kwargs):
        """
        Main hook entry point
        :param tasks:                   List of secondary tasks to be published.  Each task is a 
                                        dictionary containing the following keys:
                                        {
                                            item:   Dictionary
                                                    This is the item returned by the scan hook 
                                                    {   
                                                        name:           String
                                                        description:    String
                                                        type:           String
                                                        other_params:   Dictionary
                                                    }
                                                   
                                            output: Dictionary
                                                    This is the output as defined in the configuration - the 
                                                    primary output will always be named 'primary' 
                                                    {
                                                        name:             String
                                                        publish_template: template
                                                        tank_type:        String
                                                    }
                                        }
                        
        :param work_template:           template
                                        This is the template defined in the config that
                                        represents the current work file
               
        :param comment:                 String
                                        The comment provided for the publish
                        
        :param thumbnail:               Path string
                                        The default thumbnail provided for the publish
                        
        :param sg_task:                 Dictionary (shotgun entity description)
                                        The shotgun task to use for the publish    
                        
        :param primary_publish_path:    Path string
                                        This is the path of the primary published file as returned
                                        by the primary publish hook
                        
        :param progress_cb:             Function
                                        A progress callback to log progress during pre-publish.  Call:
                                        
                                            progress_cb(percentage, msg)
                                             
                                        to report progress to the UI
                        
        :param primary_task:            The primary task that was published by the primary publish hook.  Passed
                                        in here for reference.  This is a dictionary in the same format as the
                                        secondary tasks above.
        
        :returns:                       A list of any tasks that had problems that need to be reported 
                                        in the UI.  Each item in the list should be a dictionary containing 
                                        the following keys:
                                        {
                                            task:   Dictionary
                                                    This is the task that was passed into the hook and
                                                    should not be modified
                                                    {
                                                        item:...
                                                        output:...
                                                    }
                                                    
                                            errors: List
                                                    A list of error messages (strings) to report    
                                        }
        """
        results = []
        
        # publish all tasks:
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []

            # report progress:
            progress_cb(0, "Publishing", task)
        
            # publish alembic_cache output
            if output["name"] == "alembic_cache":
                try:
                   self.__publish_alembic_cache(item, output, work_template, primary_publish_path, 
                                                         sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                   errors.append("Publish failed - %s" % e)
            elif output["name"] == "mik_cache":
                try:
                   self.__publish_mikros_cache(item, output, work_template, primary_publish_path, 
                                                         sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                   errors.append("Publish failed - %s" % e)
            elif output["name"] == "mik_fx_cache":
                try:
                   self.__publish_mikros_fx_cache(item, output, work_template, primary_publish_path, 
                                                         sg_task, comment, thumbnail_path, progress_cb)
                except Exception, e:
                   errors.append("Publish failed - %s" % e)
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item!")

            # if there is anything to report then add to result
            if len(errors) > 0:
                # add result:
                self.parent.log_debug("")
                self.parent.log_debug("ERRORS: %s"%errors)
                self.parent.log_debug("")
                results.append({"task":task, "errors":errors})
             
            progress_cb(100)
             
        return results

    def __publish_alembic_cache(self, item, output, work_template, primary_publish_path, 
                                        sg_task, comment, thumbnail_path, progress_cb):
        """
        Publish an Alembic cache file for the scene and publish it to Shotgun.
        
        :param item:                    The item to publish
        :param output:                  The output definition to publish with
        :param work_template:           The work template for the current scene
        :param primary_publish_path:    The path to the primary published file
        :param sg_task:                 The Shotgun task we are publishing for
        :param comment:                 The publish comment/description
        :param thumbnail_path:          The path to the publish thumbnail
        :param progress_cb:             A callback that can be used to report progress
        """
        # determine the publish info to use
        #
        progress_cb(10, "Determining publish details")

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        tank_type = output["tank_type"]
                
        # create the publish path by applying the fields 
        # with the publish template:
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)
        
        # ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # determine the publish name:
        publish_name = fields.get("name")
        if not publish_name:
            publish_name = os.path.basename(publish_path)
        
        # Find additional info from the scene:
        #
        progress_cb(10, "Analysing scene")

        # set the alembic args that make the most sense when working with Mari.  These flags
        # will ensure the export of an Alembic file that contains all visible geometry from
        # the current scene together with UV's and face sets for use in Mari.
        alembic_args = ["-renderableOnly",   # only renderable objects (visible and not templated)
                        "-writeFaceSets",    # write shading group set assignments (Maya 2015+)
                        "-uvWrite"           # write uv's (only the current uv set gets written)
                        ]        

        # find the animated frame range to use:
        start_frame, end_frame = self._find_scene_animation_range()
        if start_frame and end_frame:
            alembic_args.append("-fr %d %d" % (start_frame, end_frame))

        # Set the output path: 
        # Note: The AbcExport command expects forward slashes!
        alembic_args.append("-file %s" % publish_path.replace("\\", "/"))

        # build the export command.  Note, use AbcExport -help in Maya for
        # more detailed Alembic export help
        abc_export_cmd = ("AbcExport -j \"%s\"" % " ".join(alembic_args))

        # ...and execute it:
        progress_cb(30, "Exporting Alembic cache")
        try:
            self.parent.log_debug("Executing command: %s" % abc_export_cmd)
            mel.eval(abc_export_cmd)
        except Exception, e:
            raise TankError("Failed to export Alembic Cache: %s" % e)

        # register the publish:
        progress_cb(75, "Registering the publish")        
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type
        }
        tank.util.register_publish(**args)
    
    def _find_scene_animation_range(self):
        """
        Find the animation range from the current scene.
        """
        # look for any animation in the scene:
        animation_curves = cmds.ls(typ="animCurve")
        
        # if there aren't any animation curves then just return
        # a single frame:
        if not animation_curves:
            return (1, 1)
        
        # something in the scene is animated so return the
        # current timeline.  This could be extended if needed
        # to calculate the frame range of the animated curves.
        start = int(cmds.playbackOptions(q=True, min=True))
        end = int(cmds.playbackOptions(q=True, max=True))        
        
        return (start, end)

    def __publish_mikros_cache(self, item, output, work_template, primary_publish_path, 
                                        sg_task, comment, thumbnail_path, progress_cb):
        infoNodeLib = InfoNodeLib(self.parent.engine)
        progress_cb(10, "Determining publish details")

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        wip_path = self._get_current_work_file_version(scene_path)
        fields = work_template.get_fields(wip_path)
        publish_version = fields["version"]
        tank_type = output["tank_type"]

        # determine the publish name:
        self.parent.log_debug("")
        self.parent.log_debug("  +---> Publishing Cache")
        self.parent.log_debug("  |")

        # Find additional info from the scene:
        cache = item["nodeName"]
        progress_cb(20, "Analysing scene")
        cacheType = 'geo'  ## By default, we suppose it's a geometric cache
        geomNode = cmds.cacheFile(cache, q=1, geometry=1)
        if cmds.nodeType(geomNode) == 'nParticle':
            cacheType = 'part'              
        if cmds.nodeType(geomNode) in ['fluidShape', 'nCloth']: # nFluid, nCloth
            cacheType = 'mc'

        self.parent.log_debug("  | cs_cache_type: %s"%cacheType)

        cacheDir = item["baseDir"]
        cacheName = item["baseName"]

        fields['cs_cache_type']=cacheType
        fields['cs_cache_name']=cacheName

        progress_cb(30, "Determining publish path")

         # create the publish path by applying the fields 
        # with the publish template:
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)
        publish_name = publish_path
        wantedPath = publish_path
        wantedDir = wantedPath
        wantedName = cacheName

        self.parent.log_debug("  | publish_path: %s"%publish_path)
        self.parent.log_debug("  | wantedDir: %s"%wantedDir)  
        self.parent.log_debug("  | wantedName: %s"%wantedName)  
        if cacheDir != wantedDir or cacheName != wantedName:
            self.parent.log_debug("  | Redirect %s cache directory to %s" % (cache, wantedDir))

            progress_cb(40, "Finding Files to Publish")                               
            fileList = os.listdir(cacheDir)
            if not fileList:
                self.parent.log_debug("  | Nothing to do ! No file found")
            else:
                fileList.sort()
                prct = 40
                prcPerFile = 40 / len(fileList)
                for file in fileList:                            
                    matcher = re.compile('^%s(.+)$' % cacheName).search(file)
                    if matcher:
                        source = os.path.join(cacheDir, file)
                        ender = matcher.group(1)
                        dest = '%s/%s%s' % (wantedDir, wantedName, ender)
                        if not os.path.isfile(dest):
                            self.parent.log_debug("  | => Link %s" % source)
                            self.parent.log_debug("  | => To %s" % dest)
                            infoNodeLib.do_move_and_sym_link(source, dest)
                            prct += prcPerFile
                            progress_cb(prct, "Linking %s" % (source))
                        else:
                            prct += prcPerFile
                            progress_cb(prct, "Exists Already %s" % (source))

                if cacheDir != wantedDir:
                    self.parent.log_debug("  | Set %s cache directory to %s/" % (cache, wantedDir))
                    cmds.setAttr( '%s.cachePath' % cache, '%s/' % wantedDir, type='string' )
                
                if cacheName != wantedName:
                    self.parent.log_debug("  | Set %s cache name to %s" % (cache, wantedName))
                    cmds.setAttr( '%s.cacheName' % cache, wantedName, type='string' )


        progress_cb(90, "Saving Scene with new cache")
        cmds.file(save=True, force=True)
        progress_cb(100, "Ok")
        self.parent.log_debug("  |")
        self.parent.log_debug("  |---------------------------")

    def __publish_mikros_fx_cache(self, item, output, work_template, primary_publish_path, 
                                        sg_task, comment, thumbnail_path, progress_cb):
        infoNodeLib = InfoNodeLib(self.parent.engine)
        progress_cb(10, "Determining publish details")

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        wip_path = self._get_current_work_file_version(scene_path)
        fields = work_template.get_fields(wip_path)
        publish_version = fields["version"]
        tank_type = output["tank_type"]

        # determine the publish name:
        self.parent.log_debug("")
        self.parent.log_debug("  +---> Publishing Cache")
        self.parent.log_debug("  |")

        # Find additional info from the scene:
        cache = item["nodeName"]
        cache = item['name']
        progress_cb(20, "Analysing scene")
        cacheType = 'rflow'
        self.parent.log_debug("  | cs_cache_type: %s"%cacheType)

        fields['cs_cache_type']=cacheType
        fields['cs_cache_name']=cacheName
        
        progress_cb(30, "Determining publish path")
        # create the publish path by applying the fields 
        # with the publish template:
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)

        cachePath = cmds.getAttr( '%s.Path' % cache )
        cacheEnd = re.compile('^[^\.]+').sub('', cachePath)
        wantedPath = publish_path
        wantedDir = os.path.dirname(wantedPath)
        wantedName = os.path.basename(wantedPath)
        self.parent.log_debug("  | publish_path: %s"%publish_path)
        self.parent.log_debug("  | wantedDir: %s"%wantedDir)  
        self.parent.log_debug("  | wantedName: %s"%wantedName)  
        if cachePath != wantedPath:
            self.parent.log_debug("  | Redirect %s cache directory to %s" % (cache, wantedDir))
            progress_cb(40, "Finding Files to Publish")                               
            fileList = os.listdir(cacheDir)
            if not fileList:
                self.parent.log_debug("  | Nothing to do ! No file found")
            else:
                fileList.sort()
                prct = 40
                prcPerFile = 40 / len(fileList)
                for file in fileList:
                    #print("file : %s, pattern : ^%s(\..+)$" % (file, basename))
                    matcher = re.compile('^%s(\..+)$' % basename).search(file)
                    if matcher:
                        source = '%s/%s' % (sourceDir, file)
                        ender = matcher.group(1)
                        dest = re.compile('%s$' % cacheEnd).sub(ender, wantedPath)
                        if not os.path.isfile(dest):
                            self.parent.log_debug("  | => Link %s" % source)
                            self.parent.log_debug("  | => To %s" % dest)
                            infoNodeLib.do_move_and_sym_link(source, dest)
                            prct += prcPerFile
                            progress_cb(prct, "Linking %s" % (source))
                        else:
                            prct += prcPerFile
                            progress_cb(prct, "Exists Already %s" % (source))
                    
                cmds.setAttr( '%s.Path' % cache, wantedPath, type='string' )

        progress_cb(90, "Saving Scene with new cache")
        cmds.file(save=True, force=True)
        progress_cb(100, "Ok")
        self.parent.log_debug("  |")
        self.parent.log_debug("  |---------------------------")

    def _get_current_work_file_version(self, scene_path):
        """
        Find the next available vesion for the specified work_file
        """
        self.parent.log_debug("")
        self.parent.log_debug("  +---> Get Current Work File Version From pub File")
        self.parent.log_debug("  |")
        self.parent.log_debug("  | current_file:%s"%scene_path)
        user = tank.util.get_current_user(self.parent.tank)
        path_to_wip = scene_path.replace("refOrig%s"%os.sep,"wip%s%s%s"%(os.sep,user['login'],os.sep))
        self.parent.log_debug("  | path_to_wip: %s"%path_to_wip)
        self.parent.log_debug("  |")
        self.parent.log_debug("  |---------------------------")
        return path_to_wip
