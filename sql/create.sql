--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = true;

--
-- Name: album_files; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE album_files (
    alfid integer NOT NULL,
    alid integer NOT NULL,
    fid integer NOT NULL
);


ALTER TABLE public.album_files OWNER TO database_user;

--
-- Name: album_files_alfid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE album_files_alfid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.album_files_alfid_seq OWNER TO database_user;

--
-- Name: album_files_alfid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE album_files_alfid_seq OWNED BY album_files.alfid;


--
-- Name: album_files_alid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE album_files_alid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.album_files_alid_seq OWNER TO database_user;

--
-- Name: album_files_alid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE album_files_alid_seq OWNED BY album_files.alid;


--
-- Name: album_files_fid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE album_files_fid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.album_files_fid_seq OWNER TO database_user;

--
-- Name: album_files_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE album_files_fid_seq OWNED BY album_files.fid;


--
-- Name: albums; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE albums (
    alid integer NOT NULL,
    album_name character varying(255),
    seq boolean,
    aid integer NOT NULL
);


ALTER TABLE public.albums OWNER TO database_user;

--
-- Name: albums_aid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE albums_aid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.albums_aid_seq OWNER TO database_user;

--
-- Name: albums_aid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE albums_aid_seq OWNED BY albums.aid;


--
-- Name: albums_alid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE albums_alid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.albums_alid_seq OWNER TO database_user;

--
-- Name: albums_alid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE albums_alid_seq OWNED BY albums.alid;


--
-- Name: artists; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE artists (
    aid integer NOT NULL,
    artist character varying,
    seq boolean,
    altp timestamp with time zone
);


ALTER TABLE public.artists OWNER TO database_user;

--
-- Name: artists_aid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE artists_aid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.artists_aid_seq OWNER TO database_user;

--
-- Name: artists_aid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE artists_aid_seq OWNED BY artists.aid;


SET default_with_oids = false;

--
-- Name: dont_pick; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE dont_pick (
    fid integer NOT NULL,
    reason text,
    reason_value text
);


ALTER TABLE public.dont_pick OWNER TO database_user;

--
-- Name: dont_pick_fid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE dont_pick_fid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dont_pick_fid_seq OWNER TO database_user;

--
-- Name: dont_pick_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE dont_pick_fid_seq OWNED BY dont_pick.fid;


SET default_with_oids = true;

--
-- Name: file_artists; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE file_artists (
    faid integer NOT NULL,
    fid integer NOT NULL,
    aid integer NOT NULL
);


ALTER TABLE public.file_artists OWNER TO database_user;

--
-- Name: file_artists_aid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE file_artists_aid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_artists_aid_seq OWNER TO database_user;

--
-- Name: file_artists_aid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE file_artists_aid_seq OWNED BY file_artists.aid;


--
-- Name: file_artists_faid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE file_artists_faid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_artists_faid_seq OWNER TO database_user;

--
-- Name: file_artists_faid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE file_artists_faid_seq OWNED BY file_artists.faid;


--
-- Name: file_artists_fid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE file_artists_fid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_artists_fid_seq OWNER TO database_user;

--
-- Name: file_artists_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE file_artists_fid_seq OWNED BY file_artists.fid;


--
-- Name: file_genres; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE file_genres (
    fgid integer NOT NULL,
    fid integer NOT NULL,
    gid integer NOT NULL
);


ALTER TABLE public.file_genres OWNER TO database_user;

--
-- Name: file_genres_fgid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE file_genres_fgid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_genres_fgid_seq OWNER TO database_user;

--
-- Name: file_genres_fgid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE file_genres_fgid_seq OWNED BY file_genres.fgid;


--
-- Name: file_genres_fid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE file_genres_fid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_genres_fid_seq OWNER TO database_user;

--
-- Name: file_genres_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE file_genres_fid_seq OWNED BY file_genres.fid;


--
-- Name: file_genres_gid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE file_genres_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_genres_gid_seq OWNER TO database_user;

--
-- Name: file_genres_gid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE file_genres_gid_seq OWNED BY file_genres.gid;


--
-- Name: files; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE files (
    fid integer NOT NULL,
    dir character varying(255),
    basename character varying(255),
    ltp timestamp with time zone,
    mtime timestamp with time zone
);


ALTER TABLE public.files OWNER TO database_user;

--
-- Name: files_fid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE files_fid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.files_fid_seq OWNER TO database_user;

--
-- Name: files_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE files_fid_seq OWNED BY files.fid;


--
-- Name: genres; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE genres (
    gid integer NOT NULL,
    genre text,
    enabled boolean,
    seq_genre boolean DEFAULT false
);


ALTER TABLE public.genres OWNER TO database_user;

--
-- Name: genres_gid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE genres_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.genres_gid_seq OWNER TO database_user;

--
-- Name: genres_gid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE genres_gid_seq OWNED BY genres.gid;


--
-- Name: netcast_episodes; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE netcast_episodes (
    eid integer NOT NULL,
    nid integer NOT NULL,
    episode_title text,
    episode_url text,
    local_file text
);


ALTER TABLE public.netcast_episodes OWNER TO database_user;

--
-- Name: TABLE netcast_episodes; Type: COMMENT; Schema: public; Owner: database_user
--

COMMENT ON TABLE netcast_episodes IS 'eid, nid, title, local_file, remote_url';


--
-- Name: netcast_episodes_eid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE netcast_episodes_eid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.netcast_episodes_eid_seq OWNER TO database_user;

--
-- Name: netcast_episodes_eid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE netcast_episodes_eid_seq OWNED BY netcast_episodes.eid;


--
-- Name: netcast_episodes_nid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE netcast_episodes_nid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.netcast_episodes_nid_seq OWNER TO database_user;

--
-- Name: netcast_episodes_nid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE netcast_episodes_nid_seq OWNED BY netcast_episodes.nid;


SET default_with_oids = false;

--
-- Name: netcast_subscribers; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE netcast_subscribers (
    nsid integer NOT NULL,
    nid integer NOT NULL,
    uid integer NOT NULL
);


ALTER TABLE public.netcast_subscribers OWNER TO database_user;

--
-- Name: netcast_subscribers_nid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE netcast_subscribers_nid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.netcast_subscribers_nid_seq OWNER TO database_user;

--
-- Name: netcast_subscribers_nid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE netcast_subscribers_nid_seq OWNED BY netcast_subscribers.nid;


--
-- Name: netcast_subscribers_nsid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE netcast_subscribers_nsid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.netcast_subscribers_nsid_seq OWNER TO database_user;

--
-- Name: netcast_subscribers_nsid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE netcast_subscribers_nsid_seq OWNED BY netcast_subscribers.nsid;


--
-- Name: netcast_subscribers_uid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE netcast_subscribers_uid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.netcast_subscribers_uid_seq OWNER TO database_user;

--
-- Name: netcast_subscribers_uid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE netcast_subscribers_uid_seq OWNED BY netcast_subscribers.uid;


SET default_with_oids = true;

--
-- Name: netcasts; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE netcasts (
    nid integer NOT NULL,
    netcast_name text,
    rss_url text,
    expire_time timestamp with time zone
);


ALTER TABLE public.netcasts OWNER TO database_user;

--
-- Name: netcasts_nid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE netcasts_nid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.netcasts_nid_seq OWNER TO database_user;

--
-- Name: netcasts_nid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE netcasts_nid_seq OWNED BY netcasts.nid;


SET default_with_oids = false;

--
-- Name: preload; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE preload (
    fid integer NOT NULL,
    uid integer NOT NULL,
    reason text
);


ALTER TABLE public.preload OWNER TO database_user;

--
-- Name: preload_fid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE preload_fid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.preload_fid_seq OWNER TO database_user;

--
-- Name: preload_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE preload_fid_seq OWNED BY preload.fid;


SET default_with_oids = true;

--
-- Name: tags_text; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE tags_text (
    tid integer NOT NULL,
    fid integer NOT NULL,
    tag_value text,
    tag_name text
);


ALTER TABLE public.tags_text OWNER TO database_user;

--
-- Name: tags_tid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE tags_tid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tags_tid_seq OWNER TO database_user;

--
-- Name: tags_tid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE tags_tid_seq OWNED BY tags_text.tid;


SET default_with_oids = false;

--
-- Name: tags_binary; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE tags_binary (
    btid integer DEFAULT nextval('tags_tid_seq'::regclass) NOT NULL,
    fid integer NOT NULL,
    tag_name bytea,
    tag_value bytea
);


ALTER TABLE public.tags_binary OWNER TO database_user;

--
-- Name: tags_fid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE tags_fid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tags_fid_seq OWNER TO database_user;

--
-- Name: tags_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE tags_fid_seq OWNED BY tags_text.fid;


SET default_with_oids = true;

--
-- Name: user_artist_history; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE user_artist_history (
    uahid integer NOT NULL,
    uid integer NOT NULL,
    aid integer NOT NULL,
    time_played timestamp with time zone,
    date_played date
);


ALTER TABLE public.user_artist_history OWNER TO database_user;

--
-- Name: user_artist_history_aid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_artist_history_aid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_artist_history_aid_seq OWNER TO database_user;

--
-- Name: user_artist_history_aid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_artist_history_aid_seq OWNED BY user_artist_history.aid;


--
-- Name: user_artist_history_uahid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_artist_history_uahid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_artist_history_uahid_seq OWNER TO database_user;

--
-- Name: user_artist_history_uahid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_artist_history_uahid_seq OWNED BY user_artist_history.uahid;


--
-- Name: user_artist_history_uid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_artist_history_uid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_artist_history_uid_seq OWNER TO database_user;

--
-- Name: user_artist_history_uid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_artist_history_uid_seq OWNED BY user_artist_history.uid;


--
-- Name: user_artist_info; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE user_artist_info (
    uaid integer NOT NULL,
    uid integer NOT NULL,
    aid integer NOT NULL,
    ualtp integer NOT NULL
);


ALTER TABLE public.user_artist_info OWNER TO database_user;

--
-- Name: user_artist_info_aid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_artist_info_aid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_artist_info_aid_seq OWNER TO database_user;

--
-- Name: user_artist_info_aid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_artist_info_aid_seq OWNED BY user_artist_info.aid;


--
-- Name: user_artist_info_uaid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_artist_info_uaid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_artist_info_uaid_seq OWNER TO database_user;

--
-- Name: user_artist_info_uaid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_artist_info_uaid_seq OWNED BY user_artist_info.uaid;


--
-- Name: user_artist_info_ualtp_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_artist_info_ualtp_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_artist_info_ualtp_seq OWNER TO database_user;

--
-- Name: user_artist_info_ualtp_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_artist_info_ualtp_seq OWNED BY user_artist_info.ualtp;


--
-- Name: user_artist_info_uid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_artist_info_uid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_artist_info_uid_seq OWNER TO database_user;

--
-- Name: user_artist_info_uid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_artist_info_uid_seq OWNED BY user_artist_info.uid;


--
-- Name: user_history; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE user_history (
    uhid integer NOT NULL,
    uid integer NOT NULL,
    fid integer NOT NULL,
    percent_played integer,
    time_played timestamp with time zone,
    date_played date
);


ALTER TABLE public.user_history OWNER TO database_user;

--
-- Name: user_history_fid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_history_fid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_history_fid_seq OWNER TO database_user;

--
-- Name: user_history_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_history_fid_seq OWNED BY user_history.fid;


--
-- Name: user_history_uhid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_history_uhid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_history_uhid_seq OWNER TO database_user;

--
-- Name: user_history_uhid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_history_uhid_seq OWNED BY user_history.uhid;


--
-- Name: user_history_uid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_history_uid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_history_uid_seq OWNER TO database_user;

--
-- Name: user_history_uid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_history_uid_seq OWNED BY user_history.uid;


--
-- Name: user_song_info; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE user_song_info (
    usid integer NOT NULL,
    uid integer NOT NULL,
    fid integer NOT NULL,
    rating integer DEFAULT 6,
    score integer DEFAULT 5,
    percent_played double precision DEFAULT 50.00,
    ultp timestamp with time zone,
    true_score double precision DEFAULT 50.00
);


ALTER TABLE public.user_song_info OWNER TO database_user;

--
-- Name: user_song_info_fid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_song_info_fid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_song_info_fid_seq OWNER TO database_user;

--
-- Name: user_song_info_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_song_info_fid_seq OWNED BY user_song_info.fid;


--
-- Name: user_song_info_uid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_song_info_uid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_song_info_uid_seq OWNER TO database_user;

--
-- Name: user_song_info_uid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_song_info_uid_seq OWNED BY user_song_info.uid;


--
-- Name: user_song_info_usid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE user_song_info_usid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_song_info_usid_seq OWNER TO database_user;

--
-- Name: user_song_info_usid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE user_song_info_usid_seq OWNED BY user_song_info.usid;


--
-- Name: users; Type: TABLE; Schema: public; Owner: database_user; Tablespace: 
--

CREATE TABLE users (
    uid integer NOT NULL,
    uname character varying(255),
    pword character varying(132),
    last_time_cued timestamp with time zone,
    listening boolean,
    selected boolean,
    admin boolean DEFAULT false
);


ALTER TABLE public.users OWNER TO database_user;

--
-- Name: users_uid_seq; Type: SEQUENCE; Schema: public; Owner: database_user
--

CREATE SEQUENCE users_uid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_uid_seq OWNER TO database_user;

--
-- Name: users_uid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: database_user
--

ALTER SEQUENCE users_uid_seq OWNED BY users.uid;


--
-- Name: alfid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY album_files ALTER COLUMN alfid SET DEFAULT nextval('album_files_alfid_seq'::regclass);


--
-- Name: alid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY album_files ALTER COLUMN alid SET DEFAULT nextval('album_files_alid_seq'::regclass);


--
-- Name: fid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY album_files ALTER COLUMN fid SET DEFAULT nextval('album_files_fid_seq'::regclass);


--
-- Name: alid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY albums ALTER COLUMN alid SET DEFAULT nextval('albums_alid_seq'::regclass);


--
-- Name: aid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY albums ALTER COLUMN aid SET DEFAULT nextval('albums_aid_seq'::regclass);


--
-- Name: aid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY artists ALTER COLUMN aid SET DEFAULT nextval('artists_aid_seq'::regclass);


--
-- Name: fid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY dont_pick ALTER COLUMN fid SET DEFAULT nextval('dont_pick_fid_seq'::regclass);


--
-- Name: faid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY file_artists ALTER COLUMN faid SET DEFAULT nextval('file_artists_faid_seq'::regclass);


--
-- Name: fid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY file_artists ALTER COLUMN fid SET DEFAULT nextval('file_artists_fid_seq'::regclass);


--
-- Name: aid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY file_artists ALTER COLUMN aid SET DEFAULT nextval('file_artists_aid_seq'::regclass);


--
-- Name: fgid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY file_genres ALTER COLUMN fgid SET DEFAULT nextval('file_genres_fgid_seq'::regclass);


--
-- Name: fid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY file_genres ALTER COLUMN fid SET DEFAULT nextval('file_genres_fid_seq'::regclass);


--
-- Name: gid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY file_genres ALTER COLUMN gid SET DEFAULT nextval('file_genres_gid_seq'::regclass);


--
-- Name: fid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY files ALTER COLUMN fid SET DEFAULT nextval('files_fid_seq'::regclass);


--
-- Name: gid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY genres ALTER COLUMN gid SET DEFAULT nextval('genres_gid_seq'::regclass);


--
-- Name: eid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY netcast_episodes ALTER COLUMN eid SET DEFAULT nextval('netcast_episodes_eid_seq'::regclass);


--
-- Name: nid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY netcast_episodes ALTER COLUMN nid SET DEFAULT nextval('netcast_episodes_nid_seq'::regclass);


--
-- Name: nsid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY netcast_subscribers ALTER COLUMN nsid SET DEFAULT nextval('netcast_subscribers_nsid_seq'::regclass);


--
-- Name: nid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY netcasts ALTER COLUMN nid SET DEFAULT nextval('netcasts_nid_seq'::regclass);


--
-- Name: fid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY preload ALTER COLUMN fid SET DEFAULT nextval('preload_fid_seq'::regclass);


--
-- Name: tid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY tags_text ALTER COLUMN tid SET DEFAULT nextval('tags_tid_seq'::regclass);


--
-- Name: uahid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY user_artist_history ALTER COLUMN uahid SET DEFAULT nextval('user_artist_history_uahid_seq'::regclass);


--
-- Name: uaid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY user_artist_info ALTER COLUMN uaid SET DEFAULT nextval('user_artist_info_uaid_seq'::regclass);


--
-- Name: uid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY user_artist_info ALTER COLUMN uid SET DEFAULT nextval('user_artist_info_uid_seq'::regclass);


--
-- Name: aid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY user_artist_info ALTER COLUMN aid SET DEFAULT nextval('user_artist_info_aid_seq'::regclass);


--
-- Name: ualtp; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY user_artist_info ALTER COLUMN ualtp SET DEFAULT nextval('user_artist_info_ualtp_seq'::regclass);


--
-- Name: uhid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY user_history ALTER COLUMN uhid SET DEFAULT nextval('user_history_uhid_seq'::regclass);


--
-- Name: usid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY user_song_info ALTER COLUMN usid SET DEFAULT nextval('user_song_info_usid_seq'::regclass);


--
-- Name: uid; Type: DEFAULT; Schema: public; Owner: database_user
--

ALTER TABLE ONLY users ALTER COLUMN uid SET DEFAULT nextval('users_uid_seq'::regclass);


--
-- Name: album_files_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY album_files
    ADD CONSTRAINT album_files_pkey PRIMARY KEY (alfid);


--
-- Name: albums_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY albums
    ADD CONSTRAINT albums_pkey PRIMARY KEY (alid);


--
-- Name: artists_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY artists
    ADD CONSTRAINT artists_pkey PRIMARY KEY (aid);


--
-- Name: file_artists_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY file_artists
    ADD CONSTRAINT file_artists_pkey PRIMARY KEY (faid);


--
-- Name: file_genres_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY file_genres
    ADD CONSTRAINT file_genres_pkey PRIMARY KEY (fgid);


--
-- Name: genres_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY genres
    ADD CONSTRAINT genres_pkey PRIMARY KEY (gid);


--
-- Name: netcast_episodes_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY netcast_episodes
    ADD CONSTRAINT netcast_episodes_pkey PRIMARY KEY (eid);


--
-- Name: netcast_subscribers_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY netcast_subscribers
    ADD CONSTRAINT netcast_subscribers_pkey PRIMARY KEY (nsid);


--
-- Name: netcasts_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY netcasts
    ADD CONSTRAINT netcasts_pkey PRIMARY KEY (nid);


--
-- Name: tags_binary_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY tags_binary
    ADD CONSTRAINT tags_binary_pkey PRIMARY KEY (btid);


--
-- Name: tags_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY tags_text
    ADD CONSTRAINT tags_pkey PRIMARY KEY (tid);


--
-- Name: user_artist_history_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY user_artist_history
    ADD CONSTRAINT user_artist_history_pkey PRIMARY KEY (uahid);


--
-- Name: user_artist_info_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY user_artist_info
    ADD CONSTRAINT user_artist_info_pkey PRIMARY KEY (uaid);


--
-- Name: user_history_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY user_history
    ADD CONSTRAINT user_history_pkey PRIMARY KEY (uhid);


--
-- Name: user_song_info_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY user_song_info
    ADD CONSTRAINT user_song_info_pkey PRIMARY KEY (usid);


--
-- Name: users_pkey; Type: CONSTRAINT; Schema: public; Owner: database_user; Tablespace: 
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_pkey PRIMARY KEY (uid);


--
-- Name: album_index; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX album_index ON albums USING btree (album_name);


--
-- Name: alid_fid; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX alid_fid ON album_files USING btree (alid, fid);


--
-- Name: altp_index; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX altp_index ON artists USING btree (altp);


--
-- Name: artist; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX artist ON artists USING btree (artist);


--
-- Name: dir_basename; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX dir_basename ON files USING btree (dir, basename);


--
-- Name: dont_pick_fid_index; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX dont_pick_fid_index ON dont_pick USING btree (fid);


--
-- Name: fid; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX fid ON tags_text USING btree (fid);


--
-- Name: fid_aid_index; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX fid_aid_index ON file_artists USING btree (fid, aid);


--
-- Name: ltp_index; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX ltp_index ON files USING btree (ltp);


--
-- Name: percent_played; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX percent_played ON user_song_info USING btree (percent_played);


--
-- Name: preload_fid_index; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX preload_fid_index ON preload USING btree (fid);


--
-- Name: rating; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX rating ON user_song_info USING btree (rating);


--
-- Name: skip_count; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX skip_count ON user_song_info USING btree (score);


--
-- Name: tags_binary_fid_idx; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX tags_binary_fid_idx ON tags_binary USING btree (fid);


--
-- Name: ualtp; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX ualtp ON user_artist_info USING btree (ualtp);


--
-- Name: uid_aid; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX uid_aid ON user_artist_info USING btree (uid, aid);


--
-- Name: uid_aid_date_played; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX uid_aid_date_played ON user_artist_history USING btree (uid, aid, date_played);


--
-- Name: uid_fid; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX uid_fid ON user_song_info USING btree (uid, fid);


--
-- Name: uid_fid_date_played; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX uid_fid_date_played ON user_history USING btree (uid, fid, date_played);


--
-- Name: ultp; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE INDEX ultp ON user_song_info USING btree (ultp);


--
-- Name: uname; Type: INDEX; Schema: public; Owner: database_user; Tablespace: 
--

CREATE UNIQUE INDEX uname ON users USING btree (uname);


--
-- Name: dont_pick_on_duplicate_ignore; Type: RULE; Schema: public; Owner: database_user
--

CREATE RULE dont_pick_on_duplicate_ignore AS ON INSERT TO dont_pick WHERE (EXISTS (SELECT 1 FROM dont_pick WHERE (dont_pick.fid = new.fid))) DO INSTEAD NOTHING;


--
-- Name: preload_on_duplicate_ignore; Type: RULE; Schema: public; Owner: database_user
--

CREATE RULE preload_on_duplicate_ignore AS ON INSERT TO preload WHERE (EXISTS (SELECT 1 FROM preload WHERE (preload.fid = new.fid))) DO INSTEAD NOTHING;


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

