# core python libraries
import sys
import pip
import subprocess
import os
import time
import datetime
import pandas as pd

# installs all non-core python libraries required
# --------------------------------------------------------------------------------------------------   
def install(package):
    pip.main(['install', package])

try:
    import pkg_resources
except ModuleNotFoundError:
    print("module 'pkg_resources' is not installed. Installing it now:")
    install("pkg_resources") 
    print('just installed pkg_resources, please rerun this script at your convenience')
    sys.exit(1)

# required libraries
required = {'yahoo_oauth', 'yahoo_fantasy_api', 'tqdm', 'requests', 'bs4'}
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed

if missing:
    python = sys.executable
    subprocess.check_call([python, '-m', 'pip', 'install', *missing], stdout=subprocess.DEVNULL)
 # --------------------------------------------------------------------------------------------------   

# finish imports
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
import json
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# authorization path - see readme for more details.
AUTH_PATH = '../authorization/authorization_info.json'

class YahooNBAF:
    def __init__(self): 
        # get session
        self.session = OAuth2(None, None, from_file=AUTH_PATH)
        
        # get game info
        self.__game = self.__setGame()
        self.__game_id = self.__game.game_id()

        # get league id
        try:
            json_file = open(AUTH_PATH,'r')
            data = json.load(json_file)
            self.__league_id = self.getGameKey() + '.l.' + data["league_id"] 
        except IOError:
            print('There was an error opening the authorization file! See Read Me for instructions.')
            sys.exit(1)
            
        # get league info
        self.__league = self.__setLeague()
        
        # get  your team info
        self.__team = self.__setTeam()
        
        # create a list of every team
        self.__teams = self.__setAllTeams()
        
        # store team details
        self.__team_details = self.__getTeamDetails()
    
    # private setters
    def __setGame(self):
        game = yfa.Game(self.session, 'nba')
        return game
    
    def __setLeague(self):
        league = self.__game.to_league(self.__league_id)
        return league
    
    def __setTeam(self):
        team_key = self.__league.team_key()
        team = self.__league.to_team(team_key)
        return team
    
    def __setAllTeams(self):
        teams_raw = self.__league.teams()
        teams = {tm: self.__league.to_team(tm) for tm in teams_raw}
        return teams
        
    
    # getters
    def __getTeamDetails(self):
        return self.__league.teams()
    
    def getGameKey(self):
        return self.__game_id
    
    def getLeagueID(self):
        return self.__league_id
    
    def getCurrentWeek(self):
        return self.__league.current_week()
    
    def getNumTeams(self):
        return len(self.__league.teams().keys())
    
    def getNextEditDate(self):
        return self.__league.edit_date()
    
    def getEndWeek(self):
        return self.__league.end_week()
    
    def getStandings(self):        
        return self.__league.standings()
    
    def getStatCategories(self):
        stat_categories_raw = self.__league.stat_categories()
        stat_categories = []
        for sc in stat_categories_raw:
            stat_categories.append(sc['display_name'])
        return stat_categories
    
    def getOwnership(self,player_ids):
        return self.__league.ownership(player_ids)
    
    def getMatchup(self, team_key = None, week = None):
        if week is None:
            week = self.getCurrentWeek()
        if team_key is None:
            temp_team = self.__team
        else:
            temp_team = self.__teams[team_key]
        matchup_opponent_id = temp_team.matchup(week)
        matchup_opponent_name = self.__team_details[matchup_opponent_id]['name']
        return {'team_id': matchup_opponent_id, 'team_name':matchup_opponent_name}
    
    def getRoster(self,team_key = None, day = None, week = None):
        if team_key is None:
            temp_team = self.__team
        else:
            temp_team = self.__teams[team_key]
        return temp_team.roster(week, day)
    
    def getPlayerDetails(self, plyr, stat_map):
        """
        gets current player stats
            input:
                self - YAHOONBAF object
                plyr - player details for current season
            output:
                ply_stats - dict of stats for current season ['FG%','FT%','3PT','PTS','REB','ASSITS','STEALS','BLOCKS','TOS','FGM_A','FTM_A']
        """
        # get player stats
        stat_id_map = stat_map
        stats = {}
        for stat in plyr:
            if(stat_id_map.get(stat['stat']['stat_id'])):
                stats[stat_id_map.get(stat['stat']['stat_id'])] = stat['stat']['value']
        
        # calc FGM/A and FTM/A        
        if(stats['FGA'] == '-' or stats['FGM'] == '-' or stats['FGA'] == '0' or stats['FGM'] =='0'): # 0 attempts or makes
            stats['FGM/A'] = '0/0'
        else:
            FGA = str(stats['FGA'])
            FGM = str(stats['FGM'])
            stats['FGM/A'] = FGM + '/' + FGA
        
        if(stats['FTA'] == '-' or stats['FTM'] == '-' or stats['FTA'] == '0' or stats['FTM'] =='0'): # 0 attempts or makes
            stats['FTM/A'] = '0/0'
        else:
            FTA = str(stats['FTA'])
            FTM = str(stats['FTM'])
            stats['FTM/A'] = FTM + '/' + FTA
            
        return stats
    
    def getTakenPlayersWithOwners(self, taken_player_id_list):
        """
        returns taken player id with respective owner for all taken_player_ids. Maximizes the limit of 25 queries per api call.
        """
        # get ownership - can only query 25 player ids at a time
        i=0
        taken_players_with_owners = {}
        while(i+25<len(taken_player_id_list)):
            temp_taken_players_with_owners = {}
            owners = self.getOwnership(taken_player_id_list[i:i+25])
            temp_taken_players_with_owners = {str(plyr_id) : owners[str(plyr_id)]['owner_team_name'] for plyr_id in taken_player_id_list[i:i+25]}
            taken_players_with_owners = {**taken_players_with_owners, **temp_taken_players_with_owners} # merge dicts
            i += 25
        temp_taken_players_with_owners = {}
        owners = self.getOwnership(taken_player_id_list[i:])
        temp_taken_players_with_owners = {str(plyr_id) : owners[str(plyr_id)]['owner_team_name'] for plyr_id in taken_player_id_list[i:]}
        taken_players_with_owners = {**taken_players_with_owners, **temp_taken_players_with_owners} # merge dicts
        return taken_players_with_owners
    
    def getImpactFG(self,df):
        """
        gets impact fg. impact fg defined as:
        p-P=d
        d*a=m
        where:
            p = player average
            P = league average
            d = difference of player average against league average
            a = player attempts
            m = impact score
        input:
            df - with player name and category stats
        output:
            df_impact_fg - df with included impact scores
        """        
        P = df['FG%'].mean()
            
        def attempts(x):
            a = int(x['FGM/A'].split('/')[0])
            return a
        
        df['IMPACT_FG'] = df.apply(lambda x: ((x['FG%']-P)*attempts(x)),axis=1)
        return df
    
    def getImpactFT(self,df):
        """
        gets impact ft. impact ft defined as:
        p-P=d
        d*a=m
        where:
            p = player average
            P = league average
            d = difference of player average against league average
            a = player attempts
            m = impact score
        input:
            df - with player name and category stats
        output:
            df_impact_ft - df with included impact scores
        """        
        P = df['FT%'].mean()
            
        def attempts(x):
            a = int(x['FTM/A'].split('/')[0])
            return a
        
        df['IMPACT_FT'] = df.apply(lambda x: ((x['FT%']-P)*attempts(x)),axis=1)
        return df

    # helper functions
    def createStatsLUT(self):
        """
        define a look up table for the stat names. i.e. translate ID(9007006) to ('FG%')
        """
        stat_list=self.__league.yhandler.get_settings_raw(self.__league_id)['fantasy_content']['league'][1]['settings'][0]['stat_categories']['stats']
        statsLUT = {str(stat['stat']['stat_id']): stat['stat']['value'] for stat in stat_list}
        return statsLUT
    
    def createStaticStatsLUT(self):
        """
        static stat id to stat for raw player stats.
        """
        statsLUT = {'9004003': 'FGM/A', '9007006':'FTM/A', '0': 'GP', '2': 'MIN', '3':'FGA', '4': 'FGM', '5': 'FG%', '6':'FTA', '7':'FTM',
                    '8':'FT%', '9':'3PTA', '10':'3PTM', '11':'3PT%', '12':'PTS', '13': 'OFFREB', '14': 'DEFREB', '15': 'REB', '16':'AST',
                    '17':'ST', '18': 'BLK', '19':'TO', '21':'PF'}
        return statsLUT
    
    def getAllStats(self):
        statsLUT = self.createStaticStatsLUT()
        return list(statsLUT.values())
    
    def replaceWithZero(self, df):
        """
        replaces empty stats with zero. convert stats to proper data type.
        """ 
        df['GP'] = df['GP'].replace('-','0')
        df['GP'] = df['GP'].astype(int)
        df['MIN'] = df['MIN'].replace('-','0')
        df['MIN'] = df['MIN'].astype(int)
        df['FGA'] = df['FGA'].replace('-','0')
        df['FGA'] = df['FGA'].astype(int)
        df['FGM'] = df['FGM'].replace('-','0')
        df['FGM'] = df['FGM'].astype(int)
        df['FTA'] = df['FTA'].replace('-','0')
        df['FTA'] = df['FTA'].astype(int)
        df['FTM'] = df['FTM'].replace('-','0')
        df['FTM'] = df['FTM'].astype(int)  
        df['3PTA'] = df['3PTA'].replace('-','0')
        df['3PTA'] = df['3PTA'].astype(int)  
        df['3PTM'] = df['3PTM'].replace('-','0')
        df['3PTM'] = df['3PTM'].astype(int)  
        df['OFFREB'] = df['OFFREB'].replace('-','0')
        df['OFFREB'] = df['OFFREB'].astype(int)  
        df['DEFREB'] = df['DEFREB'].replace('-','0')
        df['DEFREB'] = df['DEFREB'].astype(int) 
        df['PF'] = df['PF'].replace('-','0')
        df['PF'] = df['PF'].astype(int) 
        df['FGM/A'] = df['FGM/A'].replace('-/-', '0/0')
        df['FGM/A'] = df['FGM/A'].astype(str)
        df['FG%'] = df['FG%'].replace('-', '0')
        df['FG%'] = df['FG%'].astype(float)
        df['FTM/A'] = df['FTM/A'].replace('-/-', '0/0')
        df['FTM/A'] = df['FTM/A'].astype(str)
        df['FT%'] = df['FT%'].replace('-', '0')
        df['FT%'] = df['FT%'].astype(float)
        df['3PT%'] = df['3PT%'].replace('-', '0')
        df['3PT%'] = df['3PT%'].astype(float)
        df['3PTM'] = df['3PTM'].replace('-', '0')
        df['3PTM'] = df['3PTM'].astype(int)
        df['PTS'] = df['PTS'].replace('-', '0')
        df['PTS'] = df['PTS'].astype(int)
        df['REB'] = df['REB'].replace('-', '0')
        df['REB'] = df['REB'].astype(int)
        df['AST'] = df['AST'].replace('-', '0')
        df['AST'] = df['AST'].astype(int)
        df['ST'] = df['ST'].replace('-', '0')
        df['ST'] = df['ST'].astype(int)
        df['BLK'] = df['BLK'].replace('-', '0')
        df['BLK'] = df['BLK'].astype(int)
        df['TO'] = df['TO'].replace('-', '0')
        df['TO'] = df['TO'].astype(int)
        return df
    
    # file dump functions
    def dumpDraftResults(self):
        """
        creates a .csv file with draft results and the respective player stats
        """
        # create team map
        teams = self.__league.teams()
        game_code = self.__game_id
        team_map = {teams[e]['team_key']: teams[e]['name'] for e in teams}
        stat_map = self.createStaticStatsLUT()
        num_teams = self.getNumTeams()
        # get draft results
        draft_results = self.__league.draft_results()
        ids = [e['player_id'] for e in draft_results]
        self.__league.player_details(ids)   # Prime the player detail cache
        
        # create dataframe
        stat_columns = self.getAllStats()
        cols = ['pick', 'round', 'team', 'player'] + stat_columns
        output = pd.DataFrame(columns=cols)   
        for dp_index in tqdm(range(len(draft_results))):
            
            dp = draft_results[dp_index]
            
            plyr_details = self.__league.player_details(dp['player_id'])
            
            plyr = self.__league.yhandler.get_player_stats_raw(game_code, [dp['player_id']],'season', date = None, season = 2020)
            plyr = plyr['fantasy_content']['players']['0']['player'][1]['player_stats']['stats']

            # get draft info
            basic_info = {}
            basic_info['pick'] = dp['pick']
            basic_info['round'] = ((dp['pick']-1)//num_teams) + 1
            basic_info['team'] = team_map[dp['team_key']]
            basic_info['player'] = plyr_details[0]['name']['full']
            basic_info['position'] = plyr_details[0]['primary_position']
            
            # get stats of player
            stats = self.getPlayerDetails(plyr,stat_map)

            draft_pick_summary = {**basic_info, **stats} # merge dicts

            # append draft result to df
            output = output.append(draft_pick_summary, ignore_index=True)
            time.sleep(1)            

        
        # create impact columns
        output = self.replaceWithZero(output) # convert empty stats to 0
        output = self.getImpactFG(output)
        output = self.getImpactFT(output)
        
        # export to .csv
        outname = 'draft_results.csv'
        
        outdir = './fantasy_results/'
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        
        fullname = os.path.join(outdir, outname)    
        
        output.to_csv(fullname,index=False) 
        
        return
    
    def dumpPlayerStats(self, stat_type):
        """
        Get all player stats for a given season / last month or lat week. Note if a player is not active for the 2020 season, they will not appear in prior seasons.
        """
        # create team map
        stat_map = self.createStaticStatsLUT()
        game_code = self.__game_id
        
        # get all players
        taken_players = self.__league.taken_players()
        taken_player_id_list = [taken_plyr['player_id'] for taken_plyr in taken_players]        
        taken_players_with_owners = self.getTakenPlayersWithOwners(taken_player_id_list)
            
        waiver_players = self.__league.waivers()
        free_agents = self.__league.free_agents('P') # get all players
        all_players = taken_players+waiver_players+free_agents          

        # create dataframe
        stat_columns = self.getAllStats()
        cols = ['player_id', 'stat_type', 'name','percent_owned','status', 'ownership'] + stat_columns 
        output = pd.DataFrame(columns=cols) 
        
        total_count = 0
        print("getting stats for %s" %stat_type)
        for plyr_index in tqdm(range(len(all_players))):
            plyr = all_players[plyr_index]
            print('player %d out of %d ' %(total_count, len(all_players)))
            basic_info = {}
            basic_info['player_id'] = plyr['player_id']
            basic_info['stat_type'] = stat_type
            basic_info['name'] = plyr['name']
            basic_info['percent_owned'] = plyr['percent_owned']
            basic_info['status'] = plyr['status']
            basic_info['ownership'] = taken_players_with_owners.get(str(plyr['player_id']),'0')

            if(stat_type == 'season_2020'):
                season = 2020 
                plyr_raw_stats = self.__league.yhandler.get_player_stats_raw(game_code, [plyr['player_id']],'season', date = None, season = season)
                plyr_raw_stats = plyr_raw_stats['fantasy_content']['players']['0']['player'][1]['player_stats']['stats']
            elif(stat_type =='season_2019'):
                season = 2019
                plyr_raw_stats = self.__league.yhandler.get_player_stats_raw(game_code, [plyr['player_id']],'season', date = None, season = season)
                plyr_raw_stats = plyr_raw_stats['fantasy_content']['players']['0']['player'][1]['player_stats']['stats']                
            else:    
                plyr_raw_stats = self.__league.yhandler.get_player_stats_raw(game_code, [plyr['player_id']],stat_type, date = None, season = None)
                plyr_raw_stats = plyr_raw_stats['fantasy_content']['players']['0']['player'][1]['player_stats']['stats']

            plyr_stats = self.getPlayerDetails(plyr_raw_stats, stat_map)
            
            time.sleep(1.2)

            plyr_summary = {**basic_info, **plyr_stats} # merge dicts

            # append draft result to df
            output = output.append(plyr_summary, ignore_index=True)
            total_count = total_count + 1

        # create impact columns
        output = self.replaceWithZero(output) # convert empty stats to 0
        output = self.getImpactFG(output)
        output = self.getImpactFT(output)
        
        # export to .csv
        outname = 'player_stats_' + stat_type + '.csv'
        
        outdir = './fantasy_results/'
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        
        fullname = os.path.join(outdir, outname)    
        
        output.to_csv(fullname,index=False)             
        
        return
    
    def getGameLog(self, plyr, taken_players_with_owners, output):
        """
        uses beautiful soup and basketballreference.com to get a game log for the player
        """
        basic_info = {}
        basic_info['name'] = plyr['name']
        basic_info['player_id'] = plyr['player_id']
        basic_info['percent_owned'] = plyr['percent_owned']
        basic_info['status'] = plyr['status']
        basic_info['ownership'] = taken_players_with_owners.get(str(plyr['player_id']),'0')
        
        name_exceptions = {'clint capela': 'capelca01', 'kelan martin': 'martike03', 'kenyon martin': 'martike04', 'jamychal green': 'greenja01', 'javonte green':'greenja02',
                           'jaden mcdaneils': 'mcdanja02', 'jalen mcdaniels': 'mcdanja01', 'jalen smith': 'smithja04', 'jason smith': 'smithja02',
                           'jerami grant': 'grantje01', 'jerian grant':'grantje02', 'jacob evans':'evansja02', 'jawun evans': 'evansja01',
                           'dairis bertans':'bertada02','davis bertans':'bertada01', 'bogdan bogdanovic':'bogdabo01', 'bojan bogdanovic':'bogdabo02',
                           'mikal bridges':'bridgmi01','miles bridges':'bridgmi02', 'marcus morris':'morrima03', 'markeiff morris':'morrima02',
                           'moe harkless':'harklma01', 'cedi osman':'osmande01', 'guillermo hernangómez': 'hernawi01', 'frank ntilikina':'ntilila01',
                           'maxi kleber':'klebima01', 'kj martin': 'martike04'}
        # handle url information
        first_name = basic_info['name'].lower().split()[0].replace('.','').replace("'",'')
        last_name = basic_info['name'].lower().split()[1].replace('.','').replace("'",'')
        player_name = first_name + ' ' + last_name
        initial = last_name[0]
        if(len(last_name)>=5):
            player_id = last_name[0:5] + first_name[0:2]
        else:
            player_id = last_name+first_name[0:2]
        # name exception either for same name individuals or just random exceptions
        table = None
        name_repeat=1
        i = True    
        if name_exceptions.get(player_name,0):
            player_id = name_exceptions.get(player_name)
            name_repeat = int(player_id[-1])
            player_id = player_id[:-2]
            
        for i in range(20):
            try:
                url = 'https://www.basketball-reference.com/players/{}/{}0{}/gamelog/2021/'.format(initial, player_id, str(name_repeat))
                r = requests.get(url)
                r_html = r.text
                soup = BeautifulSoup(r_html,'html.parser')
                table=soup.findAll('table')[7].findAll('tr')
                break
            except IndexError:
                name_repeat +=1
                pass
        
        # drop column names
        table = table[1:]
        for i in range(len(table)):
            game={'stat_type': '', 'MIN': '', 'FGM': '', 'FGA':'', 'FG%': '', '3PTM': '',
                  '3PTA':'', '3PT%': '', 'FTM': '', 'FT%': '', 'FTA': '', 'PTS':'','TO':'',
                  'OFFREB':'','DEFREB':'','REB':'','AST':'','ST':'','BLK':'','PF':'','GP':''}
            reason = None
            for td in table[i].find_all("td"):
                if(td['data-stat']=='date_game'):
                    game['stat_type']=datetime.datetime.strptime(td.text, '%Y-%m-%d')
                elif(td['data-stat']=='mp'):
                    minutes = td.text
                    minutes = minutes.replace(':','.')
                    game['MIN']=int(float(minutes))
                elif(td['data-stat']=='fg'):
                    game['FGM'] = int(td.text)
                elif(td['data-stat']=='fga'):
                    game['FGA'] = int(td.text)
                elif(td['data-stat']=='fg_pct'):
                    pct = '0'+td.text
                    game['FG%'] = float(pct)
                elif(td['data-stat'] == 'fg3'):
                    game['3PTM'] = int(td.text)
                elif(td['data-stat'] == 'fg3a'):
                    game['3PTA'] = int(td.text)
                elif(td['data-stat']=='fg3_pct'):
                    pct = '0'+td.text
                    game['3PT%'] = float(pct)
                elif(td['data-stat'] == 'ft'):
                    game['FTM'] = int(td.text)
                elif(td['data-stat']=='ft_pct'):
                    pct = '0'+td.text
                    game['FT%'] = float(pct)
                elif(td['data-stat'] == 'fta'):
                    game['FTA'] = int(td.text)
                elif(td['data-stat'] == 'orb'):
                    game['OFFREB'] = int(td.text)
                elif(td['data-stat'] == 'drb'):
                    game['DEFREB'] = int(td.text)
                elif(td['data-stat'] == 'trb'):
                    game['REB'] = int(td.text)
                elif(td['data-stat'] == 'ast'):
                    game['AST'] = int(td.text)
                elif(td['data-stat'] == 'stl'):
                    game['ST'] = int(td.text)
                elif(td['data-stat'] == 'blk'):
                    game['BLK'] = int(td.text)
                elif(td['data-stat'] == 'tov'):
                    game['TO'] = int(td.text)
                elif(td['data-stat'] == 'pts'):
                    game['PTS'] = int(td.text)
                elif(td['data-stat'] == 'pf'):
                    game['PF'] = int(td.text)
                elif(td['data-stat'] == 'game_season'):
                    current_player = output[output['name']==basic_info['name']]
                    current_player_last_game = current_player[current_player['stat_type']==current_player.stat_type.max()]
                    if current_player_last_game.empty: 
                        no_games_played=True
                        current_gp = 0
                    elif current_player_last_game.GP.values[0] =='-':
                        no_games_played=True
                        current_gp = 0
                    else:
                        no_games_played = False
                        current_gp = current_player_last_game.GP.values[0]
                    if not no_games_played and not td.text =='':
                        game['GP']= int(td.text) 
                    elif no_games_played and not td.text=='':
                        game['GP'] = int(td.text)
                    else:
                        game['GP'] = current_gp
                # check to see if player was active
                if(td['data-stat'] == 'reason'):
                    reason = td.text
            # if no date - scrap it
            if game['stat_type'] == '':
                continue
            
            elif reason is None and game :
                game['FGM/A'] = '{}/{}'.format(game['FGM'],game['FGA'])
                game['FTM/A'] = '{}/{}'.format(game['FTM'],game['FTA'])
                game = {k:'-' if not v else v for k,v in game.items()}
            # empty observation
            else:
                game['FGM/A'] = '-/-'
                game['FTM/A'] = '-/-'
                game = {k:'-' if not v else v for k,v in game.items()}
            
            game_summary = {**basic_info, **game} # merge dicts
            output = output.append(game_summary,ignore_index=True)
            
        return output   
    
    def dumpDailyPlayerStats(self):
        """
        daily stats for all players up until the previous week.
        to avoid long run time and API rejections from overloading with queries we use BeautifulSoup and basketballreference.com to get a game log for all players.
        """
        # get all players
        taken_players = self.__league.taken_players()
        taken_player_id_list = [taken_plyr['player_id'] for taken_plyr in taken_players]        
        taken_players_with_owners = self.getTakenPlayersWithOwners(taken_player_id_list)
            
        waiver_players = self.__league.waivers()
        free_agents = self.__league.free_agents('P') # get all players
        all_players = taken_players+waiver_players+free_agents          

        # create dataframe
        stat_columns = self.getAllStats()
        cols = ['player_id', 'stat_type', 'name','percent_owned','status', 'ownership'] + stat_columns 
        output = pd.DataFrame(columns=cols)

        # for each week
        for plyr_index in tqdm(range(len(all_players))):
            plyr = all_players[plyr_index]
            output = self.getGameLog(plyr,taken_players_with_owners,output)  
        # create impact columns
        output = self.replaceWithZero(output) # convert empty stats to 0
        output = self.getImpactFG(output)
        output = self.getImpactFT(output)
        # write to .csv    
        outdir = './fantasy_results/'
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        outname = 'player_stats_daily_season_2020.csv'
        fullname = os.path.join(outdir, outname) 
        output.to_csv(fullname,index=False)  
        return
  
    # TODO: daily rosters
    def dumpDailyRosters(self):
        return
    # TODO: matchup results
    def dumpMatchupResults(self):
        return
    
    
    
# update output files for league
def updateFantasyLeague():
    # create class
    my_league = YahooNBAF()
    
    ######################
    # print some week info
    ######################
    print("current week: ", str(my_league.getCurrentWeek()))
    print("league ends on week number: ", str(my_league.getEndWeek()))
    print("league standings: ", my_league.getStandings())
    print("stat categories: ", my_league.getStatCategories())
    print("matchup against: ",str(my_league.getMatchup()))
    print("your current roster: ", my_league.getRoster())
    print("your opponents roster: ", my_league.getRoster(my_league.getMatchup()['team_id']))
    print("next edit date: ", my_league.getNextEditDate())
    
    #########################################
    # generate files for data vis / analytics
    #########################################
    # draft results
    # my_league.dumpDraftResults()

    # player stats
    stat_types = ['season_2020','season_2019', 'lastweek', 'lastmonth']  
    for stat_type in stat_types:
        my_league.dumpPlayerStats(stat_type)
    
    # player daily stats: using BeautifulSoup and BasketballReference.com simply because yahoo api sucks and has major query clogs.
    my_league.dumpDailyPlayerStats()

            
    
    # TODO: matchup results and matchup rosters
    # my_league.dumpLeagueResults()
    
    return


def main():
    updateFantasyLeague()


# if this script is executed (double clicked or called in cmd)
if __name__ == "__main__":
    main()

