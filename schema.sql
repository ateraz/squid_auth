create table users_all (
    user_id int(10) unsigned primary key auto_increment,
    dept_id int(10) unsigned default 0,
    login char(16) not null unique,
    passwd char(40) not null,
    admin_level tinyint(3) unsigned not null default 0
);
