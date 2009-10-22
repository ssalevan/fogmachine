import elixir

from sqlalchemy.orm import create_session,scoped_session, sessionmaker
elixir.session = scoped_session(sessionmaker(autoflush=True,
    transactional=True))

from elixir import *

#elixir/sqlalchemy specific config
metadata.bind = "mysql://fogmachine:dog8code@localhost/fogmachine?charset=utf8"
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
    guests = OneToMany('Guest', cascade='all, delete-orphan')
    using_options(tablename='host')
    
class User(Entity):
    """
    Represents a Fogmachine user, pairs a user to the guests they have checked
    out
    """
    username = Field(Unicode(255), required=True)
    password = Field(Unicode(255), required=True)
    email = Field(Unicode(255), required=True)
    is_admin = Field(Boolean, default=False)
    guests = OneToMany('Guest', cascade='all, delete-orphan')

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
    host = ManyToOne('Host', required=True, ondelete='cascade', onupdate='cascade')
    owner = ManyToOne('User', ondelete='cascade', onupdate='cascade')
    
setup_all()
create_all()
