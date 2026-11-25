'''
BEVIS is set up, it's running, but how useful is it? how many requests is it preventing reaching EPrints?

Simple idea : just track percentage of traffic that makes it through each step

another idea: can we find out how much CPU it has saved?
 if we see a request was served from the cache, can we see what the response time would have been for the first request
 which wasn't cached yet? Is this actually useful?

'''
import argparse
import gzip
import os
import datetime
import re

class Log:
    def __init__(self, log_file_path, from_date, to_date=None, high_cpu_regex="^/cgi/(search|facet|export|exportview|stats)"):
        '''
        One instance of this class will be instaniated per log file. Will support plain or gzipped log file

        only interested in processing entries from and to the dates (date, not datetime, makes it slightly easier
        in my mind to worry only about 24 hour periods)

        to_date is EXCLUSIVE, if None then we're only interested in the from_date day
        '''
        self.log_file_path = log_file_path
        self.from_date = from_date
        self.to_date = to_date #
        self.high_cpu_regex = high_cpu_regex

        self.regexes = {"high_cpu": high_cpu_regex,
                        "view": "^/view/",
                        "eprint": "^/id/"}

        self.found_entries = 0
        # self.found_high_cpu_entries = 0

        self.regex_entries = {}

    def relevant_date(self, testdate):
        return ((self.to_date is None and testdate == self.from_date) or
            (self.to_date is not None and self.from_date <= testdate < self.to_date))

    def process_line(self, line):
        '''

        :param line:
        :return:
        '''
        # try:
        line_datetime_string = line.split('[')[1].split(']')[0]
        format = "%d/%b/%Y:%H:%M:%S %z"
        line_date = datetime.datetime.strptime(line_datetime_string, format).date()
        # print(line_date)
        if self.relevant_date(line_date):
            # print(line)
            self.found_entries += 1
            get = '"GET' in line
            post = '"POST' in line
            if get or post:
                #see if this is a high cpu request
                start = '"GET' if get else '"POST'
                url = line[line.index(start) + len(start)+1:].strip()

                for regex in self.regexes:
                    if re.search(self.regexes[regex], url):
                        self.regex_entries[regex] += 1
                    # print(f"{self.log_file_path}: {line}")

            # else:
            #     if "nginx" in self.log_file_path:
            #         print(self.log_file_path, url)


    def process(self):
        self.found_entries = 0
        # self.found_high_cpu_entries = 0
        self.regex_entries = {}
        for regex in self.regexes:
            self.regex_entries[regex] = 0
        if self.log_file_path.endswith("gz"):

            with gzip.open(self.log_file_path, "rt", encoding="utf-8") as gzipfile:
                for line in gzipfile:
                    try:
                        self.process_line(line)
                    except Exception as e:
                        print(e, line)

        else:
            with open(self.log_file_path, "r", encoding="utf-8") as file:
                for line in file:
                    try:
                        self.process_line(line)
                    except Exception as e:
                        print(e, line)


class NginxLog(Log):
    '''
    turns out the log files are sufficiently similar that if we're only counting entries we don't need to distinguish
    '''
    # def process_line(self, line):
    #     '''
    #
    #     :param line:
    #     :return:
    #     '''
    #     # try:
    #     line_datetime_string = line.split('[')[1].split(']')[0]
    #     format = "%d/%b/%Y:%H:%M:%S %z"
    #     line_date = datetime.datetime.strptime(line_datetime_string, format).date()
    #     if self.relevant_date(line_date):
    #         # print(line)
    #         self.found_entries+=1

        # except Exception as e:
        #     print(e)



class ApacheLog(Log):
    '''
    only need custom logic here if doing more than just counting hits
    '''
    # def process_line(self, line):
    #     '''
    #
    #     :param line:
    #     :return:
    #     '''

def get_logs_from_dir(path, from_date, to_date=None, prefix="front_access", midfix=None, nginx=True):
    '''

    :param path:
    :param nginx:
    :return:
    '''

    # if to_date is None:
    #     # assume single day
    #     to_date = from_date + datetime.timedelta(days=1)

    # print(from_date, to_date)

    def suitable_name(filename):
        if prefix is not None and filename.startswith(prefix):
            return True
        if midfix is not None and midfix in filename:
            return True
        return False

    relevant_files = []
    for potential_file in os.scandir(path):
        if potential_file.is_file() and suitable_name(potential_file.name):
            '''
            relevant looking log file
            '''
            # TODO narrow down exactly which logs to look at. need to remember the date on the log is when it was finished, so the entries will be older
            # if nginx:
            #
            #     if "-" not in potential_file.name:
            #         # current logfile,
            #         # relevant_files.append(potential_file.name)
            #         # continue
            #         datetime_of_log = datetime.date.today()
            #     else:
            #         # after '-' and before '.'
            #         datetime_of_log_string = potential_file.name.split('-')[1].split('.')[0]
            #         datetime_of_log = datetime.date.fromisoformat(datetime_of_log_string)
            #
            #     if ((to_date is None and datetime_of_log == from_date) or
            #         (to_date is not None and datetime_of_log >= from_date and datetime_of_log <= to_date)):
            #         relevant_files.append(potential_file.name)
            relevant_files.append(potential_file.name)
                # print(potential_file, datetime_of_log)
    # print(relevant_files)

    log_class =NginxLog if nginx else ApacheLog

    logs = [log_class(os.path.join(path, relevant_file), from_date, to_date) for relevant_file in relevant_files]

    return logs


def get_hits_for_logs(logs):
    total = 0
    regex_entries = {}
    for log in logs:
        log.process()
        total += log.found_entries
        # high_cpu += log.found_high_cpu_entries
        for regex in log.regex_entries:
            if regex not in regex_entries:
                regex_entries[regex] = 0
            regex_entries[regex] += log.regex_entries[regex]
    return {"total": total, **regex_entries}

def parse_args():
    parser = argparse.ArgumentParser(description="Process the apache and nginx logs for BEVIS")
    parser.add_argument('-a', '--apache', type=str, help="Path to the apache logs", default="/var/log/httpd")
    parser.add_argument('-n', '--nginx', type=str, help="Path to the nginx logs", default="/var/log/nginx")
    parser.add_argument('-d', '--day', type=str, help="Day to process, YYYY-MM-DD", default=None)

    # TODO options for more advanced analysis, by default we will just process hits for yesterday
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    nginx_path = args.nginx#"C:/Users/lpw1r25/Documents/BEVIS notes/nginx_logs"
    apache_path = args.apache#"C:/Users/lpw1r25/Documents/BEVIS notes/apache_logs"
    examine_day = datetime.date.fromisoformat(args.day)#datetime.date(2026, 11, 18)
    if examine_day is None:
        examine_day = datetime.datetime.today().date()

    front_logs = get_logs_from_dir(nginx_path, examine_day, None, "front_access.log", nginx=True)
    front_hits = get_hits_for_logs(front_logs)

    post_anubis_logs = get_logs_from_dir(nginx_path, examine_day, None, "access.log", nginx=True)
    post_anubis_hits = get_hits_for_logs(post_anubis_logs)

    post_cache_logs = get_logs_from_dir(apache_path, examine_day, None, midfix="_eprints_access.log", nginx=False)
    post_cache_hits = get_hits_for_logs(post_cache_logs)

    # front_hits = post_anubis_hits = 0
    # print(f"Day: {examine_day} front: {front_hits} (100%) behind Anubis: {post_anubis_hits} ({100*post_anubis_hits/front_hits:.2f}%) after cache: {post_cache_hits} ({100*post_cache_hits/front_hits:.2f}%)")
    print(f"Day: {examine_day}")
    for hit_type in ["total", "high_cpu", "view", "eprint"]:
        print(
            f"{hit_type.title()} front: {front_hits[hit_type]} (100%) behind Anubis: {post_anubis_hits[hit_type]} ({100 * post_anubis_hits[hit_type] / front_hits[hit_type]:.2f}%) after cache: {post_cache_hits[hit_type]} ({100 * post_cache_hits[hit_type] / front_hits[hit_type]:.2f}%)")
