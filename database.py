from re import T
from discord.message import Attachment
from tortoise.models import MODEL, Model
from tortoise import fields

class AFK(Model):
    class Meta:
        table = "afk"
    id = fields.IntField(pk=True, null=False, generated=True)
    user_id = fields.IntField(null=False)
    message = fields.TextField(null=False)


class Submissions(Model):
    class Meta:
        table = "submissions"
    
    id = fields.IntField(pk=True, null=False, generated=True)
    user_id = fields.IntField(null=False)
    link = fields.TextField(null=True)
    title = fields.TextField(null=False)
    description = fields.TextField(null=False)
    unique_id = fields.IntField(null=False)


class Levels(Model):
    class Meta:
        table = "levels"

    id = fields.IntField(pk=True, null=False, generated=True)
    user_id = fields.IntField(null=False)
    experience = fields.IntField(null=False)
    level = fields.IntField(null=True)


class RoleBlacklist(Model):
    class Meta:
        table = "roleblacklist"
    
    id = fields.IntField(pk=True, null=False, generated=True)
    role_id = fields.IntField(null=False)


class LevelRole(Model):
    class Meta:
        table="levelrole"
    
    id = fields.IntField(pk=True, null=False, generated=True)
    level = fields.IntField(null=False)
    role_id = fields.IntField(null=False)


class BackupChannels(Model):
    class Meta:
        table = "backupchannels"
    
    id = fields.IntField(pk=True, null=False, generated=True)
    category = fields.TextField(null=True)
    type = fields.TextField(null=False)
    category_position = fields.IntField(null=True)
    channel_position = fields.IntField(null=True)
    roles = fields.TextField(null=True)
    name = fields.TextField(null=False)


class BackupMessages(Model):
    class Meta:
        table = "backupmessages"
    
    id = fields.IntField(pk=True, null=False, generated=True)
    user_id = fields.IntField(null=False)
    message = fields.TextField(null=True)
    attachment = fields.TextField(null=True)
    embed = fields.TextField(null=True)
    date_time = fields.DatetimeField(null=False)
    channel = fields.TextField(null=False)


class BackupUsers(Model):
    class Meta:
        table = "backupusers"
    id = fields.IntField(pk=True, null=False, generated=True)
    user_id = fields.IntField(null=False)
    roles = fields.TextField(null=True)

class BackupRoles(Model):
    class Meta:
        table = "backuproles"
    id = fields.IntField(pk=True, null=False, generated=True)
    rolename = fields.TextField(null=True)
    permissisons = fields.TextField(null=False)
    position = fields.IntField(null=True)
    color = fields.TextField(null=True)