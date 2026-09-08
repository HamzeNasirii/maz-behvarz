from django.db import models


class ReactionType(models.TextChoices):
    LIKE = "like", "پسندیدن"
    DISLIKE = "dislike", "نپسندیدن"