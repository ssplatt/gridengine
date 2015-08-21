#!/bin/env python
"""
user_job_stats.py - Get per users stats from GridEngine

based on http://wiki.gridengine.info/wiki/index.php/Utilities#User_Job_Stats
"""

import subprocess, sys, getopt, datetime, re

# home directory location, change if different
homedir = "/home"

def usage():
    print 'user_job_stats.py <options>\n\
        \n\
        prints the average usage per user over time\n\
        -h, --help      print this message\n\
        -t, --total     total usage only\n\
        -d #, --days=#  stats over last # days\n\
        -w, --week      stats for the week til now\n\
        -m, --month     stats for the month til now\n\
        -y, --year      stats for the year til now\
        '

class ClusterUser:
    def __init__(self,username):
        self.name = username
        self.get_fullname()
        
        #totals
        self.jobcount = 0
        self.wallclocktime = 0
        self.cputime = 0
        self.percentwallclock = 0
        
        #averages
        self.avgjobcount = 0
        self.avgwallclocktime = 0
        self.avgcputime = 0
        self.avgpercentwallclock = 0
        
    def get_fullname(self):
        output = subprocess.Popen(['getent', 'passwd', self.name], stdout=subprocess.PIPE).communicate()[0].split(':')
        if output[4]:
            self.fullname = output[4]
        else:
            self.fullname = self.name        
        
    def calc_usage(self,days):
        output = subprocess.Popen(['qacct', '-o', self.name, '-j', '-d', str(days)], stdout=subprocess.PIPE).communicate()[0]
        self.jobcount = len(re.findall('jobnumber', output))
        if self.jobcount:
            pattern = '[\s]+([\d\.]+)[\s]+([\d\.]+)[\s]+([\d\.]+)[\s]+([\d\.]+)[\s]+([\d\.]+)[\s]+([\d\.]+)[\s]+([\d\.]+)'
            matches = re.search(pattern,output)
            self.wallclocktime = float(matches.group(1))
            self.cputime = float(matches.group(4))
            self.percentwallclock = self.wallclocktime / calc_cpu_wallclock(days) / 100
            
    def calc_avg_usage(self,count):
        self.avgjobcount = self.jobcount / count
        self.avgwallclocktime = self.wallclocktime / count
        self.avgcputime = self.cputime / count
        self.avgpercentwallclock = self.percentwallclock / count
        

#function gen_human_readable_time()

def userlist():
    users = []
    userlist = subprocess.Popen(['ls',homedir], stdout=subprocess.PIPE).communicate()[0].split('\n')
    for user in userlist:
        # convert list of names to list of user objects
        # ensure no blank usernames
        if user:
            users.append(ClusterUser(user))
    return users

def calc_cpu_wallclock(days):
    output = subprocess.Popen(['qconf','-sep'], stdout=subprocess.PIPE).communicate()[0]
    match = re.search('SUM[^\w]+([\d]+)', output)
    numcpus = int(match.group(1))
    return numcpus * days * 24 * 60 * 60

def jobtotals(days,users):
    # calc total usage
    totals = {'percent_wallclock': 0, 'cpu_wallclock': 0, 'cluster_cputime': 0, 'jobcount': 0}
    
    for user in users:
        user.calc_usage(days)
        totals['percent_wallclock'] += user.percentwallclock
        totals['cpu_wallclock'] += user.wallclocktime
        totals['cluster_cputime'] += user.cputime
        totals['jobcount'] += user.jobcount
    
    return totals

def jobaverages(users):
    # calc average usage
    user_count = len(users)
    
    averages = {'percent_wallclock': 0, 'cpu_wallclock': 0, 'cluster_cputime': 0, 'jobcount': 0}
    
    for user in users:
        user.calc_avg_usage(user_count)
        averages['percent_wallclock'] += user.avgpercentwallclock
        averages['cpu_wallclock'] += user.avgwallclocktime
        averages['cluster_cputime'] += user.avgcputime
        averages['jobcount'] += user.avgjobcount
        
    return averages

def main(argv):
    try:
        opts, args = getopt.getopt(argv,"htwmyd:",["help","total","week","month","year","days="])
    except getopt.GetoptError:
        print str(err)
        usage()
        sys.exit(2)

    #initialize totals var    
    totalonly = 0

    #get command line options
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit()
        elif opt in ('-t', '--total'):
            totalonly = 1
        elif opt in ('-w', '--week'):
            days = datetime.datetime.today().isoweekday()
        elif opt in ('-m', '--month'):
            days = datetime.date.today().day
        elif opt in ('-y', '--year'):
            days = datetime.date.today().timetuple().tm_yday
        elif opt in ('-d', '--days'):
            days = int(arg)
        else:
            print str(err)
            usage()
            sys.exit()

    #start calcs
    users = userlist()
    totals = jobtotals(days,users)
    averages = jobaverages(users)

    # print output
    print "Over the last {} days:\n".format(days)

    print "Cluster Totals\n"
    print "-" * 80 + "\n"
    print "Job Count\t|\tUsed Wall Clock Time\t|\tPercent Used Wall Clock Time\t|\tCPU Time\n"
    print "-" * 80 + "\n"
    print "{}\t|\t{}\t|\t{}\t|\t{}\n".format(totals['jobcount'],totals['cpu_wallclock'],totals['percent_wallclock'],totals['cluster_cputime'])
    print "\n"
        
    print "User totals:\n"
    print "-" * 80 + "\n"
    for user in users:
        print "{}\t|\t{}\t|\t{}\t|\t{}\t|\t{}\n".format(user.fullname,user.jobcount,user.cputime,user.wallclocktime,user.percentwallclock)
    
    if not totalonly:
        print "Cluster Averages\n"
        print "-" * 80 + "\n"
        print "Job Count\t|\tUsed Wall Clock Time\t|\tPercent Used Wall Clock Time\t|\tCPU Time\n"
        print "-" * 80 + "\n"
        print "{}\t|\t{}\t|\t{}\t|\t{}\n".format(averages['jobcount'],averages['cpu_wallclock'],averages['percent_wallclock'],averages['cluster_cputime'])
        print "\n"
        
        print "User averages:\n"
        print "-" * 80 + "\n"
        for user in users:
            print "{}\t|\t{}\t|\t{}\t|\t{}\t|\t{}\n".format(user.fullname,user.avgjobcount,user.avgcputime,user.avgwallclocktime,user.avgpercentwallclock)
    

# run main
if __name__ == "__main__":
   main(sys.argv[1:])