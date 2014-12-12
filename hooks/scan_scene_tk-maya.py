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
import maya.cmds as cmds

import tank
from tank import Hook
from tank import TankError

class ScanSceneHook(Hook):
    """
    Hook to scan scene for items to publish
    """
    
    def execute(self, **kwargs):
        """
        Main hook entry point
        :returns:       A list of any items that were found to be published.  
                        Each item in the list should be a dictionary containing 
                        the following keys:
                        {
                            type:   String
                                    This should match a scene_item_type defined in
                                    one of the outputs in the configuration and is 
                                    used to determine the outputs that should be 
                                    published for the item
                                    
                            name:   String
                                    Name to use for the item in the UI
                            
                            description:    String
                                            Description of the item to use in the UI
                                            
                            selected:       Bool
                                            Initial selected state of item in the UI.  
                                            Items are selected by default.
                                            
                            required:       Bool
                                            Required state of item in the UI.  If True then
                                            item will not be deselectable.  Items are not
                                            required by default.
                                            
                            other_params:   Dictionary
                                            Optional dictionary that will be passed to the
                                            pre-publish and publish hooks
                        }
        """   
                
        items = []
        
        # get the main scene:
        scene_name = cmds.file(query=True, sn=True)
        if not scene_name:
            raise TankError("Please Save your file before Publishing")
        
        scene_path = os.path.abspath(scene_name)
        name = os.path.basename(scene_path)

        # create the primary item - this will match the primary output 'scene_item_type':            
        items.append({"type": "work_file", "name": name})
        
        # if there is any geometry in the scene (poly meshes or nurbs patches), then
        # add a geometry item to the list:
        if cmds.ls(geometry=True, noIntermediate=True):
            items.append({"type":"geometry", "name":"All Scene Geometry"})

        cmds.pluginInfo( "realflow", q=1, l=1 )
        if cmds.pluginInfo( "realflow", q=1, l=1 ):
            cacheList = cmds.ls( type='RealflowMesh' )
            if cacheList:
                for cache in cacheList:
                    items.append({"type":"mik_fx_cache", "name":"<b style='color:yellow;'>%s </b>"%cache})

        cacheList = cmds.ls(type='cacheFile')
        if cacheList:
            for cache in cacheList:
                baseDir = cmds.getAttr("%s.cachePath"%cache)
                baseName = cmds.getAttr("%s.cacheName"%cache)
                items.append({"type":"mik_cache", "name":"<b style='color:yellow;'>%s </b>"%cache,"baseDir":baseDir,"baseName":baseName,"nodeName":cache})
        
        if "LGT" in scene_path:
            lgt_template = self.parent.tank.templates['maya_shot_render_mono_exr']
            work_template = self.parent.tank.templates['maya_shot_work']
            fields = work_template.get_fields(scene_path)

            lgt_renders = lgt_template.apply_fields(fields)
            baseName = os.path.basename(lgt_renders)
            dirName = os.path.dirname(lgt_renders)
            if os.path.exists(dirName):
                files = os.listdir(dirName)
                self.parent.log_debug("dirname : %s"%dirName)
                for i,myFile in enumerate(files):
                    if i>4:
                        self.parent.log_debug("f: %s ... and more"%myFile)
                        break
                    self.parent.log_debug("f: %s"%myFile)

                if  len(files)>0:
                    newFiles = ["%s%s%s"%(dirName,os.sep,f) for f in files]
                    items.append({"name":"Lighting Renders Node: %s" % dirName,
                                          "type":"lgt_renders",
                                          "description":"Renders for shot: %s" % dirName,"renderFolder":dirName,"lgt_renders":lgt_renders,"files":newFiles})
                 
        return items
