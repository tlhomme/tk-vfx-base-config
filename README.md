## Config schema ( folder hierarchy )
+ **Prod Root**
 + _admin
 + _editorial
 + _presentation
 + _source_global
 + **assets**
     + asset-type
     + asset
        + pipeline_step

 + **shots**
     + sequence
        + shot
           + pipeline_step

## Custom template paths
### Custom Mapping with existing fields
**project name**
```yaml
cs_project:
    type: str
    shotgun_entity_type: Project
    shotgun_field_name: sg_tank_name
```

**user name**
```yaml
cs_user_name:
    type: str
    shotgun_entity_type: HumanUser
    shotgun_field_name: login
```

**asset type**
```yaml
cs_asset_type:
    type: str
    shotgun_entity_type: Asset
    shotgun_field_name: sg_asset_type
```

### Custom Mapping with new fields

**pipeline step short-name**
```yaml
cs_step_short_name:
    type: str
    shotgun_entity_type: Step
    shotgun_field_name: short_name
```

**task name**
```yaml
cs_task_name:
    type: str
    shotgun_entity_type: Task
    shotgun_field_name: sg_task_code
```
### Custom key, no fields : only for file naming

**publi flag for wip files**
```yaml
cs_publi_flag:
    type: str
```

## Custom Apps:
* **tk-multi-worfiles-mik**: created to fit the mikros folder hierarchy and vfx work methodology
   * changed default config to always start a new version number when creating (saving) a new variant.
   * changed default behavior to always show all current work files for a given asset
   * changed versionning to keep track of all work files across artists

## Custom Hooks:
### apps level:
* **tk-multi-publish**:
   * **primary_publish.py**: added changes to file versionning to mimic mikros existing vfx pipeline
   * **post_publish.py**: added changes post-publish to remove "publi" flag in file name after publish to version up.
* **tk-multi-loader2**:
   * **tk-maya-actions.py**: changed default behavior for referencing to target unversioned published file at root of the pipeline-step folder. ( mikros default behavior)