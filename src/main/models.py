from django.db import models

# Create your models here.
class nrlData2(models.Model):
    round = models.CharField(("Round"), max_length=255)
    date = models.DateField(("Date"))
    homeTeam = models.CharField(("Home Team"), max_length=255)
    homeScore = models.IntegerField(("Home Score"))
    awayTeam = models.CharField(("Away Team"), max_length=255)
    awayScore = models.IntegerField(("Away Score"))
    season = models.IntegerField(("Season"))
    margin = models.IntegerField(("Margin"))
    homeELO = models.FloatField(("Home ELO"))
    awayELO = models.FloatField(("Away ELO"))
    predictedMargin = models.FloatField("Predicted")
