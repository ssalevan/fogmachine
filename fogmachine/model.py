from elixir import *

metadata.bind = "sqlite:///fogmachine.sqlite"
metadata.bind.echo = False

class Host(Entity):
    cobbler_name = Field(Unicode(255), required=True)
    guests = OneToMany('Guest')
    
class User(Entity):
    username = Field(Unicode(255), required=True)
    password = Field(Unicode(255), required=True)
    guests = OneToMany('Guest')

class Guest(Entity):
    cobbler_name = Field(Unicode(255), required=True)
    virt_name = Field(Unicode(255), required=True)
    host = ManyToOne('Host', required=True)
    owner = ManyToOne('User')
    expire_date = Field(DateTime, required=True)
    purpose = Field(Unicode(255), default="It is a mystery...")
    
setup_all()
create_all()
