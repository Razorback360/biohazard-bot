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