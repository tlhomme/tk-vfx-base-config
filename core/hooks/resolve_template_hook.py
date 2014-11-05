# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
This hook is used to resolve template context name at execution time
"""

from tank import Hook
import os

class ProceduralTemplateEvaluator(Hook):

    def execute(self, setting, bundle_obj, extra_params, **kwargs):
        """
        returns: needs to return the name of a template, as a string.
        """
        debug =  bundle_obj.log_debug
        template_key = extra_params[0]
        context = bundle_obj.context
        entity = context.entity
        engine = bundle_obj.engine.name
        template_name = ""
        debug("entity: %s"%entity)
        debug("engine: %s"%engine)
        debug("template_key: %s"%template_key)

        if entity:
            if "area" in template_key:
                template_name = "%s_%s_%s"%(entity["type"].lower(),template_key,engine[3:])
            else:
                template_name = "%s_%s_%s"%(engine[3:],entity["type"].lower(),template_key)
        elif "project" in template_key:
            template_name = "%s_%s"%(engine[3:],template_key)

        debug("template_name: %s"%template_name)
        return template_name

