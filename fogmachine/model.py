from elixir import *

#elixir/sqlalchemy specific config
metadata.bind = "sqlite:///fogmachine.sqlite"
metadata.bind.echo = True
metadata.bind.autocommit = True

class Host(Entity):
    hostname = Field(Unicode(255), required=True)
    connection = Field(Unicode(255), required=True)
    free_mem = Field(Integer)
    guests = OneToMany('Guest')
    
class User(Entity):
    username = Field(Unicode(255), required=True)
    password = Field(Unicode(255), required=True)
    email = Field(Unicode(255), required=True)
    is_admin = Field(Boolean, default=False)
    guests = OneToMany('Guest')

class Guest(Entity):
    virt_name = Field(Unicode(255), required=True)
    cobbler_profile = Field(Unicode(255), required=True)
    expire_date = Field(DateTime, required=True)
    purpose = Field(Unicode(255), default="It is a mystery...")
    state = Field(Unicode(255), default="unchecked")
    host = ManyToOne('Host', required=True)
    owner = ManyToOne('User')
    
setup_all()
create_all()
