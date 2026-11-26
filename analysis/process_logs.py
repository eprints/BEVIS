'''
BEVIS is set up, it's running, but how useful is it? how many requests is it preventing reaching EPrints?

Simple idea : just track percentage of traffic that makes it through each step

another idea: can we find out how much CPU it has saved?
 if we see a request was served from the cache, can we see what the response time would have been for the first request
 which wasn't cached yet? Is this actually useful?

'''
import argparse
import gzip
import json
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

        self.keys = ["total"] + [key for key in self.regexes.keys()]

        ''
        self.results = {}

    # def safe_add(self, add_to_dict, key, value):
    #     if key not in add_to_dict:
    #

    def relevant_date(self, testdate):
        return ((self.to_date is None and testdate == self.from_date) or
            (self.to_date is not None and self.from_date <= testdate < self.to_date))


    def get_datetime_from_line(self, line):
        line_datetime_string = line.split('[')[1].split(']')[0]
        format = "%d/%b/%Y:%H:%M:%S %z"
        line_time = datetime.datetime.strptime(line_datetime_string, format)
        return line_time

    def get_datetime_key(self, a_datetime):
        dateonly = a_datetime.date()
        return f"{dateonly}:{a_datetime.hour:02d}00"

    @staticmethod
    def safe_add_to_dict(original_dict, *keys, add=1):
        '''
        increment an int in a nest of dicts, assuming that the last key is for the int.
        If any of the dicts or keys don't exist along the way, create them
        :param original_dict:
        :param keys:
        :param add:
        :return:
        '''
        relevant_dict = original_dict
        for key in keys[:-1]:
            if key not in relevant_dict:
                relevant_dict[key] = {}
            relevant_dict = relevant_dict[key]
        if keys[-1] not in relevant_dict:
            relevant_dict[keys[-1]] = 0

        relevant_dict[keys[-1]] += add

    @staticmethod
    def safe_get_from_dict(original_dict, *keys):
        '''
        Same as safe_add_to_dict, but return zero if the keys don't exist
        :param original_dict:
        :param keys:
        :return:
        '''
        relevant_dict = original_dict
        for key in keys:
            if key not in relevant_dict:
                return 0
            relevant_dict = relevant_dict[key]

        return relevant_dict

    def process_line(self, line):
        '''

        :param line:
        :return:
        '''
        # try:
        line_time = self.get_datetime_from_line(line)
        line_date = line_time.date()

        datetime_key = self.get_datetime_key(line_time)

        if self.relevant_date(line_date):
            # print(line)
            # self.results["all"]["total"]["hits"] += 1
            self.safe_add_to_dict(self.results, "all", "total", "hits")
            # self.results[datetime_key]["total"]["hits"] += 1
            self.safe_add_to_dict(self.results, datetime_key, "total", "hits")

            if 'HTTP/1.1" 503 ' in line:
                # self.results["all"]["total"]["rate_limited"] += 1
                self.safe_add_to_dict(self.results, "all", "total", "rate_limited")
                # self.results[datetime_key]["total"]["rate_limited"] += 1
                self.safe_add_to_dict(self.results, datetime_key, "total", "rate_limited")

            get = '"GET' in line
            post = '"POST' in line
            if get or post:
                #see if this is a high cpu request
                start = '"GET' if get else '"POST'
                url = line[line.index(start) + len(start)+1:].strip()

                for regex in self.regexes:
                    if re.search(self.regexes[regex], url):
                        if 'HTTP/1.1" 503 ' in line:
                            # self.results["all"][regex]["rate_limited"] += 1
                            self.safe_add_to_dict(self.results, "all", regex, "rate_limited")
                            # self.results[datetime_key][regex]["rate_limited"] += 1
                            self.safe_add_to_dict(self.results, datetime_key, regex, "rate_limited")
                        # self.results["all"][regex]["hits"] += 1
                        self.safe_add_to_dict(self.results, "all", regex, "hits")
                        # self.results[datetime_key][regex]["hits"] += 1
                        self.safe_add_to_dict(self.results, datetime_key, regex, "hits")



    # def get_empty_results_inner_dict(self):
    #     results = {}
    #     # results["all"] = {}
    #     # for hour in range(24):
    #     #     results[hour] = {}
    #     for key in self.keys:
    #         results[key] = {"hits": 0, "rate_limited": 0}
    #         # for hour in range(24):
    #         #     results[hour][key] = {"hits": 0, "rate_limited": 0}
    #     return results

    def is_logfile_relevant(self):
        if self.log_file_path.endswith("gz"):
            #actually takes longer to try and do this with a gziped file, just check first line
            with gzip.open(self.log_file_path, "rb") as gzipfile:
                return self.is_logfile_relevant_inner(gzipfile, firstline_only=True)
            # return True
        else:
            with open(self.log_file_path, "rb") as file:
                return self.is_logfile_relevant_inner(file)

    def is_logfile_relevant_inner(self, file, firstline_only=False):
        #check the last entry, if it's before the relevant day we can skip processing the entire log
        try:
            if not firstline_only:
                file.seek(-2, os.SEEK_END)
                while file.read(1) != b'\n':
                    file.seek(-2, os.SEEK_CUR)

                last_line = file.readline().decode()

                line_time = self.get_datetime_from_line(last_line)
                line_date = line_time.date()

                if line_date < self.from_date:
                    # latest entry is too old, skip file
                    return False


            file.seek(0)
            first_line = file.readline().decode()
            line_time = self.get_datetime_from_line(first_line)
            line_date = line_time.date()
            if self.to_date is None and line_date > self.from_date + datetime.timedelta(days=1):
                # the oldest entry is too new
                return False
        except Exception as e:
            print(e, self.log_file_path)

        file.seek(0)
        return True



    def process(self):
        self.results = {}#self.get_empty_results_dict()
        if not self.is_logfile_relevant():
            print(f"{self.log_file_path} is not relevant")
            return

        print(f"Processing {self.log_file_path}")

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

class ApacheLog(Log):
    '''
    only need custom logic here if doing more than just counting hits
    '''

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




class BEVISProcessor:
    '''
    Use the processed logs of each stage to produce useful statistics
    '''
    def get_all_time_keys(self):
        return ["all"] + [time for time in range(24)]

    def __init__(self, front_logs, post_anubis_logs, post_cache_logs):
        self.front_hits = self.get_hits_for_logs(front_logs)
        self.post_anubis_hits = self.get_hits_for_logs(post_anubis_logs)
        self.post_cache_hits = self.get_hits_for_logs(post_cache_logs)

        self.processed_results = {}

        all_time_keys = []
        all_keys = front_logs[0].keys[:]

        for logfile in front_logs:
            all_time_keys += [time_key for time_key in logfile.results]

        #list of sets to make unique
        for time_key in list(set(all_time_keys)):
            self.processed_results[time_key] = {}
            for key in all_keys:
                try:
                    self.processed_results[time_key][key] = self.process_logset(self.front_hits[time_key], self.post_anubis_hits[time_key], self.post_cache_hits[time_key], key)
                except Exception as e:
                    print(f"Unable to process results for {time_key}, {key}: {e}")

    def get_hits_for_logs(self, logs):

        results = {}#logs[0].get_empty_results_dict()

        for log in logs:
            log.process()

            for time_key in log.results:
                for key in log.results[time_key]:
                    # results[time_key][key]["hits"] += log.results[time_key][key]["hits"]
                    Log.safe_add_to_dict(results, time_key, key, "hits", add=Log.safe_get_from_dict(log.results,time_key, key, "hits"))
                    # results[time_key][key]["rate_limited"] += log.results[time_key][key]["rate_limited"]
                    Log.safe_add_to_dict(results, time_key, key, "rate_limited", add=Log.safe_get_from_dict(log.results, time_key, key, "rate_limited"))

        return results

    def process_logset(self, front_hits, post_anubis_hits, post_cache_hits, hit_type):
        '''
        Assume this is either the total or a single hour.
        percentages are of the TOTAL traffic, not what hits that layer
        '''

        total_hits = Log.safe_get_from_dict(front_hits, hit_type, "hits")

        if total_hits != 0:
            anubis_pass = 100 * Log.safe_get_from_dict(post_anubis_hits, hit_type, "hits") / total_hits
        else:
            anubis_pass = 0
        anubis_blocked = 100 - anubis_pass



        #how many were 503ed by the final nginx, will appear in the second nginx log
        rate_limited_count = Log.safe_get_from_dict(post_anubis_hits, hit_type, "rate_limited")
        if total_hits != 0:
            rate_limited = 100 * rate_limited_count / total_hits
        else:
            rate_limited = 0

        # how many were stopped by the final nginx (missing from the apache log)
        hit_cache_and_rate_limit_count = Log.safe_get_from_dict(post_anubis_hits, hit_type, "hits") - Log.safe_get_from_dict(post_cache_hits, hit_type, "hits")
        hit_cache_count = hit_cache_and_rate_limit_count - rate_limited_count
        if total_hits != 0:
            hit_cache = 100* hit_cache_count/ total_hits
        else:
            hit_cache = 0

        reached_eprints_total_count = Log.safe_get_from_dict(post_cache_hits, hit_type, "hits")
        if total_hits != 0:
            reached_eprints_total = 100 * reached_eprints_total_count / total_hits
        else:
            reached_eprints_total = 0

        return {
            "front_total": total_hits,
            "post_anubis_total": Log.safe_get_from_dict(post_anubis_hits, hit_type, "hits"),
            "post_cache_total" : Log.safe_get_from_dict(post_cache_hits, hit_type, "hits"),
            "rate_limit_blocked_total": rate_limited_count,
            "anubis_blocked_count":  Log.safe_get_from_dict(front_hits, hit_type, "hits") - Log.safe_get_from_dict(post_anubis_hits, hit_type, "hits"),
            "anubis_blocked": 100 - anubis_pass,

            "rate_limited" : rate_limited,
            "hit_cache_count": hit_cache_count,
            "hit_cache": hit_cache,
            "reached_eprints_total_count": reached_eprints_total_count,
            "reached_eprints_total" : reached_eprints_total
        }



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
    # front_hits = get_hits_for_logs(front_logs)

    post_anubis_logs = get_logs_from_dir(nginx_path, examine_day, None, "access.log", nginx=True)
    # post_anubis_hits = get_hits_for_logs(post_anubis_logs)

    post_cache_logs = get_logs_from_dir(apache_path, examine_day, None, midfix="_eprints_access.log", nginx=False)
    # post_cache_hits = get_hits_for_logs(post_cache_logs)

    # front_hits = post_anubis_hits = 0
    # print(f"Day: {examine_day} front: {front_hits} (100%) behind Anubis: {post_anubis_hits} ({100*post_anubis_hits/front_hits:.2f}%) after cache: {post_cache_hits} ({100*post_cache_hits/front_hits:.2f}%)")
    print(f"Day: {examine_day}")
    print("All percentages are fractions of the total front hits")

    processor = BEVISProcessor(front_logs, post_anubis_logs, post_cache_logs)

    # print(json.dumps(processor.processed_results, indent=2))

    for time_key in sorted([key for key in processor.processed_results]):
        print(f"{time_key} : Total hits {processor.processed_results[time_key]['total']['front_total']} Anubis blocked {processor.processed_results[time_key]['total']['anubis_blocked']:.1f}% Cache hit {processor.processed_results[time_key]['total']['hit_cache']:.1f}% Rate limited {processor.processed_results[time_key]['total']['rate_limited']:.1f}% Reached EPrints {processor.processed_results[time_key]['total']['reached_eprints_total']:.1f}% ({processor.processed_results[time_key]['total']['reached_eprints_total_count']})")

    with open("results.json", "w") as jsonfile:
        json.dump(processor.processed_results, jsonfile, indent=2)

    #
    # def print_results(front_hits, post_anubis_hits, post_cache_hits, hit_types):
    #     for hit_type in hit_types:
    #         try:
    #             # front_hits =  front_hits[hit_type]
    #             anubis_pass = 100 * post_anubis_hits[hit_type] / front_hits[hit_type]
    #             anubis_blocked = 100 - anubis_pass
    #             cache_pass_of_total = 100 * post_cache_hits[hit_type] / front_hits[hit_type]
    #             cache_pass = 100 * post_cache_hits[hit_type] / post_anubis_hits[hit_type]
    #             cache_blocked = 100 - cache_pass
    #             print(
    #                 f"{hit_type.title()} front: {front_hits[hit_type]} (100%) behind Anubis: {post_anubis_hits[hit_type]} (blocked {anubis_blocked:.0f}%) after cache: {post_cache_hits[hit_type]}, (blocked {cache_blocked:.0f}%), {cache_pass_of_total:.1f}% reached EPrints")
    #         except Exception as e:
    #             print(e)
    #
    # print("Total:")
    # print_results(front_hits["total"], post_anubis_hits["total"], post_cache_hits["total"], ["total", "high_cpu", "view", "eprint"])
    #
    # for hour in range(24):
    #     print(f"Hour {hour}:")
    #     print_results(front_hits["per_hour"][hour], post_anubis_hits["per_hour"][hour], post_cache_hits["per_hour"][hour], ["total"])
