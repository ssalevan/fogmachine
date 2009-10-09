from elixir import *

#elixir/sqlalchemy specific config
metadata.bind = "sqlite:///fogmachine.sqlite"
metadata.bind.echo = False
metadata.bind.autocommit = True

class Host(Entity):
    """
    Represents a Virtualized Host in the database, contains information
    pertaining to its attributes
    """
    hostname = Field(Unicode(255), required=True)
    connection = Field(Unicode(255), required=True)
    virt_type = Field(Unicode(255), required=True)
    free_mem = Field(Integer)
    num_guests = Field(Integer)
    guests = OneToMany('Guest')
    
class User(Entity):
    """
    Represents a Fogmachine user, pairs a user to the guests they have checked
    out
    """
    username = Field(Unicode(255), required=True)
    password = Field(Unicode(255), required=True)
    email = Field(Unicode(255), required=True)
    is_admin = Field(Boolean, default=False)
    guests = OneToMany('Guest')

class Guest(Entity):
    """
    Represents a Virtualized Guest, paired it to its corresponding Host object
    and the User that created it
    """
    virt_name = Field(Unicode(255), required=True)
    cobbler_profile = Field(Unicode(255), required=True)
    expire_date = Field(DateTime, required=True)
    purpose = Field(Unicode(255), default=u"It is a mystery...")
    state = Field(Unicode(255), default=u"unchecked")
    mac_address = Field(Unicode(255))
    ip_address = Field(Unicode(255))
    hostname = Field(Unicode(255))
    vnc_port = Field(Unicode(255))
    host = ManyToOne('Host', required=True)
    owner = ManyToOne('User')
    
setup_all()
create_all()
