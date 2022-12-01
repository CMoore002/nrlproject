from django.http import HttpResponse
from django.shortcuts import render
from .models import nrlData2
import datetime
import re
import requests
from bs4 import BeautifulSoup
import numpy as np

# Create your views here.
def homeView(request,*args, **kwargs):
    ##Declaring Variables
    competitionType = '111'
    logValue = 28

    ##Formulas for ELO
    actualOutcome = lambda x: 1 - 0.5**(1+x/130)
    predictedOutcome = lambda homeElo, awayElo: 1/(1+10**((awayElo - homeElo - homeGroundAdvantage)/100))
    predictedMargins = lambda x: 130*np.log((1-x)/0.5)/np.log(0.5)
    flatteningElo = lambda x: np.exp(1-(9000 + x)/10000)*x
    homeGroundAdvantage = 1
    ratingConstant = lambda x : 2*np.log(x)

    ##Making dictionary for getting round number
    roundDict = {
        "FinalsWeek1" : 28,
        "FinalsWeek2" : 29,
        "FinalsWeek3" : 30,
        "GrandFinal" : 31
    }
    teamNamesList = [
        'Broncos', 'Bulldogs', 'Cowboys', 'Dragons',
        'Eels', 'Knights', 'Panthers', 'Rabbitohs',
        'Raiders', 'Roosters', 'SeaEagles', 'Sharks',
        'Storm', 'Titans', 'Warriors', 'WestsTigers',
        'Dolphins'
    ]   
    teamDict = {}

    for x in teamNamesList:
        teamDict[x] = 1000
    
    ##Defining function
    def removeCharacters(string):
        """
        Function returns the string without special characters
        """
        return re.sub('\W+', '', string)
    ##Get round and season from last entry in database
    getRound = nrlData2.objects.values('round').last()['round']
    getSeason = nrlData2.objects.values('season').last()['season']

    ##Filtering data to show on front end. Showing the round from last entry of the last entries season

    dataList = nrlData2.objects.filter(round=getRound).filter(season=getSeason)
 

    ##Checking if date has exceeded the last game played. If it does then scrape for new round
    ##and update database
    dateToday = datetime.date.today()
    getDate = nrlData2.objects.values('date').last()
    if(dateToday > getDate['date']):
        #########################################################################################################
        ##Getting round number
        if getRound in roundDict:
            roundNumber = roundDict[getRound]
        else:
            roundNumber = re.sub('\D', '', getRound)

        #########################################################################################################
        ##Getting last rounds scores and inserting into database
        ##Requesting page source
        page = requests.get('https://www.nrl.com/draw/?competition={}&round={}&season={}'
                            .format(competitionType, roundNumber, getSeason))

        ##Parsing with BeautifulSoup
        soup = BeautifulSoup(page.content, 'html.parser')

        ##Getting data from page. Finding the class and then searching q-data in the div element
        roundData = str(soup.find(class_="u-spacing-mt-24")['q-data'])

        ##Splitting each match into it's own entry in list. Index 0 is useless information, 
        ##therefore start at 1.
        matchList = []
        for text in roundData.split('matchCentreUrl'):
            matchList.append(text)

        ##Finding Date of Match
        dateData = []
        for x in range(1, len(matchList)):
            dateData.append(matchList[x].split('"kickOffTimeLong":')[1].split(',')[0].split('T')[0].replace('"', ''))
            
        ##Finding score Data
        ##the index for scoreData is (x-1) because the loop starts at 1
        scoreData = []
        for x in range(1, len(matchList)):
            scoreData.append([removeCharacters(y.split(':')[1]) for y in matchList[x].split(',') if "score" in y])
            
        for x in range(1, len(matchList)):
            tempData = nrlData2.objects.filter(date=dateData[x-1])
            #tempData.homeScore = int(scoreData[x-1][0])
            #tempData.awayScore = int(scoreData[x-1][1])
            updateMargin = int(scoreData[x-1][0]) - int(scoreData[x-1][1])
            tempData.update(homeScore = int(scoreData[x-1][0]), awayScore = int(scoreData[x-1][1]),
                            margin = int(updateMargin))

        #########################################################################################################
        ##Updating ELO
        for x in teamDict:
            try:
                latestHomeGame = nrlData2.objects.filter(homeTeam=x).values('date').last()
                latestHomeGame2 = latestHomeGame['date']
            except:
                latestHomeGame2 = datetime.date(1,1,1)

            try:
                latestAwayGame = nrlData2.objects.filter(awayTeam=x).values('date').last()
                latestAwayGame2 = latestAwayGame['date']
            except:
                latestAwayGame2 = datetime.date(1,1,1)

            if latestHomeGame2 > latestAwayGame2:
                ##Do home game stuff
                homeMargin = nrlData2.objects.values('margin').filter(date=latestHomeGame2).filter(homeTeam=x)[0]['margin']
                oldRatingHome = nrlData2.objects.values('homeELO').filter(date=latestHomeGame2).filter(homeTeam=x)[0]['homeELO']
                oldRatingAway = nrlData2.objects.values('awayELO').filter(date=latestHomeGame2).filter(homeTeam=x)[0]['awayELO']
                teamDict[x] = oldRatingHome + ratingConstant(logValue/2)*(actualOutcome(homeMargin) 
                - predictedOutcome(oldRatingHome, oldRatingAway))
            elif latestHomeGame2 < latestAwayGame2:
                ##Do away game stuff
                awayMargin = nrlData2.objects.values('margin').filter(date=latestAwayGame2).filter(awayTeam=x)[0]['margin']
                oldRatingHome = nrlData2.objects.values('homeELO').filter(date=latestAwayGame2).filter(awayTeam=x)[0]['homeELO']
                oldRatingAway = nrlData2.objects.values('awayELO').filter(date=latestAwayGame2).filter(awayTeam=x)[0]['awayELO']
                teamDict[x] = oldRatingAway + ratingConstant(logValue/2)*(-actualOutcome(awayMargin)
                + predictedOutcome(oldRatingHome, oldRatingAway))
            if getRound == 'GrandFinal':
                teamDict[x] = flatteningElo(teamDict[x])

        #########################################################################################################
        ##Get the latest round info
        ##Update Last Rounds Scores
        if getRound == 'GrandFinal':
            getSeason += 1
            roundNumber = 1
        else:
            roundNumber += 1

        ##Requesting page source
        page = requests.get('https://www.nrl.com/draw/?competition={}&round={}&season={}'
                    .format(competitionType, roundNumber, getSeason))

        ##Parsing with BeautifulSoup
        soup = BeautifulSoup(page.content, 'html.parser')

        ##Getting data from page. Finding the class and then searching q-data in the div element
        roundData = str(soup.find(class_="u-spacing-mt-24")['q-data'])

        ##Splitting each match into it's own entry in list. Index 0 is useless information, 
        ##therefore start at 1.
        matchList = []
        for text in roundData.split('matchCentreUrl'):
            matchList.append(text)
            
        ##Finding Round Number. Finds first occurrence of '"roundTitle":' and splits. Split again to get 
        ##round number
        roundList = []
        for x in range(1, len(matchList)):
            roundList.append(removeCharacters(roundData.split('"roundTitle":')[1].split(',')[0]))

        ##Finding Date of Match
        dateData = []
        seasonData = []
        for x in range(1, len(matchList)):
            dateData.append(matchList[x].split('"kickOffTimeLong":')[1].split(',')[0].split('T')[0].replace('"', ''))
            seasonData.append(matchList[x].split('"kickOffTimeLong":')[1].split(',')[0].split('T')[0].replace('"', '').split('-')[0])

        ##Finding Team Name Data
        ##the index for teamData is (x-1) because the loop starts at 1
        teamData = []
        homeList = []
        awayList = []
        for x in range(1, len(matchList)):
            teamData.append([removeCharacters(y.split(':')[1]) for y in matchList[x].split(',') if "nickName" in y])
            homeList.append(teamData[x-1][0])
            awayList.append(teamData[x-1][1])

        ##id/round/date/homeTeam/homeScore/awayTeam/awayScore/margin/homeELO/awayELO/predictedMargin
        for x in range(len(matchList)-1):
            nrlData2.objects.create(
                round = roundList[x],
                date = dateData[x],
                homeTeam = homeList[x],
                homeScore = 0,
                awayTeam = awayList[x],
                awayScore = 0,
                season = getSeason,
                margin = 0,
                homeELO = teamDict[homeList[x]],
                awayELO = teamDict[awayList[x]],
                predictedMargin = predictedMargins(predictedOutcome(teamDict[homeList[x]], teamDict[awayList[x]]))
            )


    return render(request, "home.html", {'dataList': dataList, 'roundNumber':getRound, 'seasonNumber':getSeason})