import re
from model import Host, session

def _read_config(file_loc):
    cfg_file = open(file_loc, 'r')
    cfg_lines = cfg_file.readlines()
    entries = []
    for line in cfg_lines:
        # strip comments/surrounding whitespace
        line = re.sub("#.*","",line).strip()
        # check if line matches comma-separated entry pattern
        if(re.match(".*,.*",line)):
            entry = line.split(',')
            entries.append((unicode(entry[0].strip()),
                unicode(entry[1].strip())))
    cfg_file.close()
    return entries
    
def add_hosts(file_loc):
    all_hosts = _read_config(file_loc)
    # clean out hosts no longer present
    for host in Host.query.all():
        if not (host.hostname, host.connection) in all_hosts:
            session.delete(host)
            session.commit()
    # add new hosts (if any)
    for host in _read_config(file_loc):
        if not Host.get_by(hostname=host[0]):
            print "Host: %s, %s" % (host[0], host[1])
            newhost = Host(hostname=host[0],
                connection=host[1])
    session.commit()
