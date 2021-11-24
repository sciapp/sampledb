--
-- PostgreSQL database dump
--

-- Dumped from database version 11.4
-- Dumped by pg_dump version 11.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: authenticationtype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.authenticationtype AS ENUM (
    'LDAP',
    'EMAIL',
    'OTHER',
    'API_TOKEN'
);


--
-- Name: filelogentrytype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.filelogentrytype AS ENUM (
    'OTHER',
    'EDIT_TITLE',
    'EDIT_DESCRIPTION',
    'HIDE_FILE',
    'UNHIDE_FILE'
);


--
-- Name: httpmethod; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.httpmethod AS ENUM (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS',
    'OTHER'
);


--
-- Name: instrumentlogcategorytheme; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.instrumentlogcategorytheme AS ENUM (
    'GRAY',
    'BLUE',
    'GREEN',
    'YELLOW',
    'RED'
);


--
-- Name: notificationmode; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.notificationmode AS ENUM (
    'IGNORE',
    'WEBAPP',
    'EMAIL'
);


--
-- Name: notificationtype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.notificationtype AS ENUM (
    'OTHER',
    'ASSIGNED_AS_RESPONSIBLE_USER',
    'INVITED_TO_GROUP',
    'INVITED_TO_PROJECT',
    'ANNOUNCEMENT',
    'RECEIVED_OBJECT_PERMISSIONS_REQUEST',
    'INSTRUMENT_LOG_ENTRY_CREATED',
    'REFERENCED_BY_OBJECT_METADATA',
    'INSTRUMENT_LOG_ENTRY_EDITED'
);


--
-- Name: objectlogentrytype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.objectlogentrytype AS ENUM (
    'OTHER',
    'CREATE_OBJECT',
    'EDIT_OBJECT',
    'RESTORE_OBJECT_VERSION',
    'USE_OBJECT_IN_MEASUREMENT',
    'POST_COMMENT',
    'UPLOAD_FILE',
    'USE_OBJECT_IN_SAMPLE_CREATION',
    'CREATE_BATCH',
    'ASSIGN_LOCATION',
    'LINK_PUBLICATION',
    'REFERENCE_OBJECT_IN_METADATA',
    'EXPORT_TO_DATAVERSE',
    'LINK_PROJECT',
    'UNLINK_PROJECT'
);


--
-- Name: permissions; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.permissions AS ENUM (
    'NONE',
    'READ',
    'WRITE',
    'GRANT'
);


--
-- Name: userlogentrytype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.userlogentrytype AS ENUM (
    'OTHER',
    'CREATE_OBJECT',
    'EDIT_OBJECT',
    'EDIT_OBJECT_PERMISSIONS',
    'REGISTER_USER',
    'INVITE_USER',
    'EDIT_USER_PREFERENCES',
    'RESTORE_OBJECT_VERSION',
    'POST_COMMENT',
    'UPLOAD_FILE',
    'CREATE_BATCH',
    'ASSIGN_LOCATION',
    'CREATE_LOCATION',
    'UPDATE_LOCATION',
    'LINK_PUBLICATION',
    'CREATE_INSTRUMENT_LOG_ENTRY'
);


--
-- Name: usertype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.usertype AS ENUM (
    'PERSON',
    'OTHER'
);


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: action_translations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_translations (
    id integer NOT NULL,
    language_id integer,
    action_id integer,
    name character varying NOT NULL,
    description character varying NOT NULL,
    short_description character varying NOT NULL
);


--
-- Name: action_translations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.action_translations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: action_translations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.action_translations_id_seq OWNED BY public.action_translations.id;


--
-- Name: action_type_translations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_type_translations (
    id integer NOT NULL,
    language_id integer,
    action_type_id integer,
    name character varying NOT NULL,
    description character varying NOT NULL,
    object_name character varying NOT NULL,
    object_name_plural character varying NOT NULL,
    view_text character varying NOT NULL,
    perform_text character varying NOT NULL
);


--
-- Name: action_type_translations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.action_type_translations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: action_type_translations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.action_type_translations_id_seq OWNED BY public.action_type_translations.id;


--
-- Name: action_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_types (
    id integer NOT NULL,
    admin_only boolean NOT NULL,
    show_on_frontpage boolean NOT NULL,
    show_in_navbar boolean NOT NULL,
    enable_labels boolean NOT NULL,
    enable_files boolean NOT NULL,
    enable_locations boolean NOT NULL,
    enable_publications boolean NOT NULL,
    enable_comments boolean NOT NULL,
    enable_activity_log boolean NOT NULL,
    enable_related_objects boolean NOT NULL,
    enable_project_link boolean DEFAULT false NOT NULL
);


--
-- Name: action_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.action_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: action_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.action_types_id_seq OWNED BY public.action_types.id;


--
-- Name: actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.actions (
    id integer NOT NULL,
    type_id integer NOT NULL,
    instrument_id integer,
    schema json NOT NULL,
    user_id integer,
    description_is_markdown boolean NOT NULL,
    is_hidden boolean NOT NULL,
    short_description_is_markdown boolean NOT NULL
);


--
-- Name: actions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.actions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: actions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.actions_id_seq OWNED BY public.actions.id;


--
-- Name: api_log_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_log_entries (
    id integer NOT NULL,
    api_token_id integer NOT NULL,
    method public.httpmethod NOT NULL,
    route character varying NOT NULL,
    utc_datetime timestamp without time zone NOT NULL
);


--
-- Name: api_log_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.api_log_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: api_log_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.api_log_entries_id_seq OWNED BY public.api_log_entries.id;


--
-- Name: association; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.association (
    instrument_id integer,
    user_id integer
);


--
-- Name: authentications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.authentications (
    id integer NOT NULL,
    user_id integer,
    login jsonb,
    type public.authenticationtype,
    confirmed boolean NOT NULL
);


--
-- Name: authentications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.authentications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: authentications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.authentications_id_seq OWNED BY public.authentications.id;


--
-- Name: comments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comments (
    id integer NOT NULL,
    object_id integer NOT NULL,
    user_id integer NOT NULL,
    content text NOT NULL,
    utc_datetime timestamp without time zone NOT NULL
);


--
-- Name: comments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.comments_id_seq OWNED BY public.comments.id;


--
-- Name: dataverse_exports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dataverse_exports (
    object_id integer NOT NULL,
    dataverse_url character varying NOT NULL,
    user_id integer NOT NULL,
    utc_datetime timestamp without time zone NOT NULL
);


--
-- Name: default_group_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.default_group_permissions (
    creator_id integer NOT NULL,
    group_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: default_project_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.default_project_permissions (
    creator_id integer NOT NULL,
    project_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: default_public_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.default_public_permissions (
    creator_id integer NOT NULL,
    is_public boolean NOT NULL
);


--
-- Name: default_user_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.default_user_permissions (
    creator_id integer NOT NULL,
    user_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: favorite_actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.favorite_actions (
    action_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: favorite_instruments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.favorite_instruments (
    instrument_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: file_log_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.file_log_entries (
    id integer NOT NULL,
    type public.filelogentrytype NOT NULL,
    object_id integer NOT NULL,
    file_id integer NOT NULL,
    user_id integer NOT NULL,
    data json NOT NULL,
    utc_datetime timestamp without time zone NOT NULL
);


--
-- Name: file_log_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.file_log_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: file_log_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.file_log_entries_id_seq OWNED BY public.file_log_entries.id;


--
-- Name: files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.files (
    id integer NOT NULL,
    object_id integer NOT NULL,
    user_id integer NOT NULL,
    utc_datetime timestamp without time zone NOT NULL,
    data json
);


--
-- Name: group_action_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.group_action_permissions (
    action_id integer NOT NULL,
    group_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: group_invitations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.group_invitations (
    id integer NOT NULL,
    group_id integer NOT NULL,
    user_id integer NOT NULL,
    inviter_id integer NOT NULL,
    utc_datetime timestamp without time zone NOT NULL,
    accepted boolean NOT NULL
);


--
-- Name: group_invitations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.group_invitations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: group_invitations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.group_invitations_id_seq OWNED BY public.group_invitations.id;


--
-- Name: group_object_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.group_object_permissions (
    object_id integer NOT NULL,
    group_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: group_project_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.group_project_permissions (
    project_id integer NOT NULL,
    group_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.groups (
    id integer NOT NULL,
    name json NOT NULL,
    description json NOT NULL
);


--
-- Name: groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.groups_id_seq OWNED BY public.groups.id;


--
-- Name: instrument_log_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instrument_log_categories (
    id integer NOT NULL,
    instrument_id integer NOT NULL,
    title character varying NOT NULL,
    theme public.instrumentlogcategorytheme NOT NULL
);


--
-- Name: instrument_log_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instrument_log_categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instrument_log_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instrument_log_categories_id_seq OWNED BY public.instrument_log_categories.id;


--
-- Name: instrument_log_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instrument_log_entries (
    id integer NOT NULL,
    instrument_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: instrument_log_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instrument_log_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instrument_log_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instrument_log_entries_id_seq OWNED BY public.instrument_log_entries.id;


--
-- Name: instrument_log_entry_version_category_associations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instrument_log_entry_version_category_associations (
    log_entry_id integer,
    log_entry_version_id integer,
    category_id integer
);


--
-- Name: instrument_log_entry_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instrument_log_entry_versions (
    log_entry_id integer NOT NULL,
    version_id integer NOT NULL,
    content text NOT NULL,
    utc_datetime timestamp without time zone NOT NULL,
    content_is_markdown boolean DEFAULT false NOT NULL,
    event_utc_datetime timestamp without time zone
);


--
-- Name: instrument_log_file_attachments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instrument_log_file_attachments (
    id integer NOT NULL,
    log_entry_id integer NOT NULL,
    file_name character varying NOT NULL,
    content bytea NOT NULL,
    is_hidden boolean NOT NULL
);


--
-- Name: instrument_log_file_attachments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instrument_log_file_attachments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instrument_log_file_attachments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instrument_log_file_attachments_id_seq OWNED BY public.instrument_log_file_attachments.id;


--
-- Name: instrument_log_object_attachments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instrument_log_object_attachments (
    id integer NOT NULL,
    log_entry_id integer NOT NULL,
    object_id integer NOT NULL,
    is_hidden boolean NOT NULL
);


--
-- Name: instrument_log_object_attachments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instrument_log_object_attachments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instrument_log_object_attachments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instrument_log_object_attachments_id_seq OWNED BY public.instrument_log_object_attachments.id;


--
-- Name: instrument_translations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instrument_translations (
    id integer NOT NULL,
    instrument_id integer,
    language_id integer,
    name character varying NOT NULL,
    description character varying NOT NULL,
    notes character varying NOT NULL,
    short_description character varying NOT NULL
);


--
-- Name: instrument_translations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instrument_translations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instrument_translations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instrument_translations_id_seq OWNED BY public.instrument_translations.id;


--
-- Name: instruments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instruments (
    id integer NOT NULL,
    users_can_create_log_entries boolean NOT NULL,
    users_can_view_log_entries boolean NOT NULL,
    create_log_entry_default boolean NOT NULL,
    is_hidden boolean NOT NULL,
    notes_is_markdown boolean,
    description_is_markdown boolean,
    short_description_is_markdown boolean NOT NULL,
    notes text DEFAULT ''::text NOT NULL
);


--
-- Name: instruments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instruments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instruments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instruments_id_seq OWNED BY public.instruments.id;


--
-- Name: languages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.languages (
    id integer NOT NULL,
    lang_code character varying NOT NULL,
    names json NOT NULL,
    datetime_format_datetime character varying,
    datetime_format_moment character varying,
    enabled_for_input boolean NOT NULL,
    enabled_for_user_interface boolean DEFAULT false NOT NULL
);


--
-- Name: languages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.languages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: languages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.languages_id_seq OWNED BY public.languages.id;


--
-- Name: locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locations (
    id integer NOT NULL,
    name json NOT NULL,
    description json NOT NULL,
    parent_location_id integer
);


--
-- Name: locations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.locations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: locations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.locations_id_seq OWNED BY public.locations.id;


--
-- Name: markdown_images; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.markdown_images (
    file_name text NOT NULL,
    content bytea NOT NULL,
    user_id integer,
    utc_datetime timestamp without time zone,
    permanent boolean NOT NULL
);


--
-- Name: markdown_to_html_cache_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.markdown_to_html_cache_entries (
    id integer NOT NULL,
    markdown text NOT NULL,
    parameters jsonb NOT NULL,
    html text NOT NULL
);


--
-- Name: markdown_to_html_cache_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.markdown_to_html_cache_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: markdown_to_html_cache_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.markdown_to_html_cache_entries_id_seq OWNED BY public.markdown_to_html_cache_entries.id;


--
-- Name: migration_index; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.migration_index (
    migration_index integer
);


--
-- Name: notification_mode_for_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_mode_for_types (
    id integer NOT NULL,
    type public.notificationtype,
    user_id integer NOT NULL,
    mode public.notificationmode NOT NULL
);


--
-- Name: notification_mode_for_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notification_mode_for_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notification_mode_for_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notification_mode_for_types_id_seq OWNED BY public.notification_mode_for_types.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    type public.notificationtype NOT NULL,
    user_id integer NOT NULL,
    data json NOT NULL,
    was_read boolean NOT NULL,
    utc_datetime timestamp without time zone NOT NULL
);


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: object_location_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.object_location_assignments (
    id integer NOT NULL,
    object_id integer NOT NULL,
    location_id integer,
    responsible_user_id integer,
    user_id integer NOT NULL,
    description json NOT NULL,
    utc_datetime timestamp without time zone NOT NULL,
    confirmed boolean NOT NULL
);


--
-- Name: object_location_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.object_location_assignments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: object_location_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.object_location_assignments_id_seq OWNED BY public.object_location_assignments.id;


--
-- Name: object_log_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.object_log_entries (
    id integer NOT NULL,
    type public.objectlogentrytype NOT NULL,
    object_id integer NOT NULL,
    user_id integer NOT NULL,
    data json NOT NULL,
    utc_datetime timestamp without time zone NOT NULL
);


--
-- Name: object_log_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.object_log_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: object_log_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.object_log_entries_id_seq OWNED BY public.object_log_entries.id;


--
-- Name: object_publications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.object_publications (
    object_id integer NOT NULL,
    doi character varying NOT NULL,
    title character varying,
    object_name character varying
);


--
-- Name: objects_current; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.objects_current (
    object_id integer NOT NULL,
    version_id integer NOT NULL,
    action_id integer NOT NULL,
    data jsonb NOT NULL,
    schema jsonb NOT NULL,
    user_id integer NOT NULL,
    utc_datetime timestamp without time zone NOT NULL
);


--
-- Name: objects_current_object_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.objects_current_object_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: objects_current_object_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.objects_current_object_id_seq OWNED BY public.objects_current.object_id;


--
-- Name: objects_previous; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.objects_previous (
    object_id integer NOT NULL,
    version_id integer NOT NULL,
    action_id integer NOT NULL,
    data jsonb NOT NULL,
    schema jsonb NOT NULL,
    user_id integer NOT NULL,
    utc_datetime timestamp without time zone NOT NULL
);


--
-- Name: project_action_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_action_permissions (
    action_id integer NOT NULL,
    project_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: project_invitations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_invitations (
    id integer NOT NULL,
    project_id integer NOT NULL,
    user_id integer NOT NULL,
    inviter_id integer NOT NULL,
    utc_datetime timestamp without time zone NOT NULL,
    accepted boolean NOT NULL
);


--
-- Name: project_invitations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_invitations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_invitations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_invitations_id_seq OWNED BY public.project_invitations.id;


--
-- Name: project_object_association; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_object_association (
    project_id integer NOT NULL,
    object_id integer NOT NULL
);


--
-- Name: project_object_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_object_permissions (
    object_id integer NOT NULL,
    project_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id integer NOT NULL,
    name json NOT NULL,
    description json NOT NULL
);


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: public_actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.public_actions (
    action_id integer NOT NULL
);


--
-- Name: public_objects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.public_objects (
    object_id integer NOT NULL
);


--
-- Name: settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.settings (
    user_id integer NOT NULL,
    data json NOT NULL
);


--
-- Name: subproject_relationship; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subproject_relationship (
    parent_project_id integer NOT NULL,
    child_project_id integer NOT NULL,
    child_can_add_users_to_parent boolean NOT NULL
);


--
-- Name: tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tags (
    id integer NOT NULL,
    name character varying NOT NULL,
    uses integer NOT NULL
);


--
-- Name: tags_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tags_id_seq OWNED BY public.tags.id;


--
-- Name: user_action_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_action_permissions (
    action_id integer NOT NULL,
    user_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: user_group_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_group_memberships (
    user_id integer,
    group_id integer
);


--
-- Name: user_invitations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_invitations (
    id integer NOT NULL,
    inviter_id integer NOT NULL,
    utc_datetime timestamp without time zone NOT NULL,
    accepted boolean NOT NULL
);


--
-- Name: user_invitations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_invitations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_invitations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_invitations_id_seq OWNED BY public.user_invitations.id;


--
-- Name: user_log_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_log_entries (
    id integer NOT NULL,
    type public.userlogentrytype NOT NULL,
    user_id integer NOT NULL,
    data json NOT NULL,
    utc_datetime timestamp without time zone NOT NULL
);


--
-- Name: user_log_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_log_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_log_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_log_entries_id_seq OWNED BY public.user_log_entries.id;


--
-- Name: user_object_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_object_permissions (
    object_id integer NOT NULL,
    user_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: user_project_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_project_permissions (
    project_id integer NOT NULL,
    user_id integer NOT NULL,
    permissions public.permissions NOT NULL
);


--
-- Name: user_object_permissions_by_all; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.user_object_permissions_by_all AS
 SELECT NULL::integer AS user_id,
    public_objects.object_id,
    1 AS permissions_int
   FROM public.public_objects
UNION
 SELECT association.user_id,
    objects.object_id,
    3 AS permissions_int
   FROM ((public.association association
     JOIN public.actions actions ON ((association.instrument_id = actions.instrument_id)))
     JOIN public.objects_current objects ON ((objects.action_id = actions.id)))
UNION
 SELECT user_object_permissions.user_id,
    user_object_permissions.object_id,
    (('{"READ": 1, "GRANT": 3, "WRITE": 2}'::jsonb ->> (user_object_permissions.permissions)::text))::integer AS permissions_int
   FROM public.user_object_permissions
UNION
 SELECT user_group_memberships.user_id,
    group_object_permissions.object_id,
    (('{"READ": 1, "GRANT": 3, "WRITE": 2}'::jsonb ->> (group_object_permissions.permissions)::text))::integer AS permissions_int
   FROM (public.user_group_memberships user_group_memberships
     JOIN public.group_object_permissions group_object_permissions ON ((user_group_memberships.group_id = group_object_permissions.group_id)))
UNION
 SELECT user_project_permissions.user_id,
    project_object_permissions.object_id,
    LEAST((('{"READ": 1, "GRANT": 3, "WRITE": 2}'::jsonb ->> (project_object_permissions.permissions)::text))::integer, (('{"READ": 1, "GRANT": 3, "WRITE": 2}'::jsonb ->> (user_project_permissions.permissions)::text))::integer) AS permissions_int
   FROM (public.user_project_permissions user_project_permissions
     JOIN public.project_object_permissions project_object_permissions ON ((user_project_permissions.project_id = project_object_permissions.project_id)))
UNION
 SELECT user_group_memberships.user_id,
    project_object_permissions.object_id,
    LEAST((('{"READ": 1, "GRANT": 3, "WRITE": 2}'::jsonb ->> (project_object_permissions.permissions)::text))::integer, (('{"READ": 1, "GRANT": 3, "WRITE": 2}'::jsonb ->> (group_project_permissions.permissions)::text))::integer) AS permissions_int
   FROM ((public.user_group_memberships user_group_memberships
     JOIN public.group_project_permissions ON ((group_project_permissions.group_id = user_group_memberships.group_id)))
     JOIN public.project_object_permissions project_object_permissions ON ((group_project_permissions.project_id = project_object_permissions.project_id)));


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying NOT NULL,
    email character varying NOT NULL,
    type public.usertype NOT NULL,
    is_admin boolean NOT NULL,
    is_readonly boolean NOT NULL,
    is_hidden boolean NOT NULL,
    orcid character varying,
    affiliation character varying,
    is_active boolean NOT NULL,
    role character varying,
    extra_fields json DEFAULT '{}'::json NOT NULL
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: action_translations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_translations ALTER COLUMN id SET DEFAULT nextval('public.action_translations_id_seq'::regclass);


--
-- Name: action_type_translations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_type_translations ALTER COLUMN id SET DEFAULT nextval('public.action_type_translations_id_seq'::regclass);


--
-- Name: action_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_types ALTER COLUMN id SET DEFAULT nextval('public.action_types_id_seq'::regclass);


--
-- Name: actions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions ALTER COLUMN id SET DEFAULT nextval('public.actions_id_seq'::regclass);


--
-- Name: api_log_entries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_log_entries ALTER COLUMN id SET DEFAULT nextval('public.api_log_entries_id_seq'::regclass);


--
-- Name: authentications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authentications ALTER COLUMN id SET DEFAULT nextval('public.authentications_id_seq'::regclass);


--
-- Name: comments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments ALTER COLUMN id SET DEFAULT nextval('public.comments_id_seq'::regclass);


--
-- Name: file_log_entries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_log_entries ALTER COLUMN id SET DEFAULT nextval('public.file_log_entries_id_seq'::regclass);


--
-- Name: group_invitations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_invitations ALTER COLUMN id SET DEFAULT nextval('public.group_invitations_id_seq'::regclass);


--
-- Name: groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups ALTER COLUMN id SET DEFAULT nextval('public.groups_id_seq'::regclass);


--
-- Name: instrument_log_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_categories ALTER COLUMN id SET DEFAULT nextval('public.instrument_log_categories_id_seq'::regclass);


--
-- Name: instrument_log_entries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_entries ALTER COLUMN id SET DEFAULT nextval('public.instrument_log_entries_id_seq'::regclass);


--
-- Name: instrument_log_file_attachments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_file_attachments ALTER COLUMN id SET DEFAULT nextval('public.instrument_log_file_attachments_id_seq'::regclass);


--
-- Name: instrument_log_object_attachments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_object_attachments ALTER COLUMN id SET DEFAULT nextval('public.instrument_log_object_attachments_id_seq'::regclass);


--
-- Name: instrument_translations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_translations ALTER COLUMN id SET DEFAULT nextval('public.instrument_translations_id_seq'::regclass);


--
-- Name: instruments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instruments ALTER COLUMN id SET DEFAULT nextval('public.instruments_id_seq'::regclass);


--
-- Name: languages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.languages ALTER COLUMN id SET DEFAULT nextval('public.languages_id_seq'::regclass);


--
-- Name: locations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations ALTER COLUMN id SET DEFAULT nextval('public.locations_id_seq'::regclass);


--
-- Name: markdown_to_html_cache_entries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.markdown_to_html_cache_entries ALTER COLUMN id SET DEFAULT nextval('public.markdown_to_html_cache_entries_id_seq'::regclass);


--
-- Name: notification_mode_for_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_mode_for_types ALTER COLUMN id SET DEFAULT nextval('public.notification_mode_for_types_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: object_location_assignments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_location_assignments ALTER COLUMN id SET DEFAULT nextval('public.object_location_assignments_id_seq'::regclass);


--
-- Name: object_log_entries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_log_entries ALTER COLUMN id SET DEFAULT nextval('public.object_log_entries_id_seq'::regclass);


--
-- Name: objects_current object_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.objects_current ALTER COLUMN object_id SET DEFAULT nextval('public.objects_current_object_id_seq'::regclass);


--
-- Name: project_invitations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_invitations ALTER COLUMN id SET DEFAULT nextval('public.project_invitations_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: tags id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags ALTER COLUMN id SET DEFAULT nextval('public.tags_id_seq'::regclass);


--
-- Name: user_invitations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_invitations ALTER COLUMN id SET DEFAULT nextval('public.user_invitations_id_seq'::regclass);


--
-- Name: user_log_entries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_log_entries ALTER COLUMN id SET DEFAULT nextval('public.user_log_entries_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: action_translations; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.action_translations VALUES (2, -99, 2, 'Alternative Process', 'This is an example action', '');
INSERT INTO public.action_translations VALUES (3, -99, 3, 'Sample Creation (Batch)', 'This is an example action', '');
INSERT INTO public.action_translations VALUES (1, -99, 1, 'Updated Sample Creation', '', '');
INSERT INTO public.action_translations VALUES (4, -99, 4, 'XRR Measurement', '', '');
INSERT INTO public.action_translations VALUES (5, -99, 5, 'Searchable Object', '', '');
INSERT INTO public.action_translations VALUES (6, -99, 6, 'Perform Measurement', '', '');
INSERT INTO public.action_translations VALUES (7, -99, 7, 'Perform Measurement', '', '');
INSERT INTO public.action_translations VALUES (8, -99, 8, 'Perform Measurement', '', '');
INSERT INTO public.action_translations VALUES (9, -99, 9, 'Other Sample', '', '');
INSERT INTO public.action_translations VALUES (10, -99, 10, 'sample_action', '', '');
INSERT INTO public.action_translations VALUES (11, -99, 11, 'measurement_action', '', '');
INSERT INTO public.action_translations VALUES (12, -99, 12, 'Plotly Example Action', '', '');
INSERT INTO public.action_translations VALUES (13, -99, 13, 'Plotly Array Example Action', '', '');
INSERT INTO public.action_translations VALUES (14, -99, 14, 'choices translation test', '', '');


--
-- Data for Name: action_type_translations; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.action_type_translations VALUES (1, -99, -99, 'Sample Creation', 'These Actions represent processes which create a sample.', 'Sample', 'Samples', 'View Samples', 'Create Sample');
INSERT INTO public.action_type_translations VALUES (2, -99, -98, 'Measurement', 'These Actions represent processes which perform a measurement.', 'Measurement', 'Measurements', 'View Measurements', 'Perform Measurement');
INSERT INTO public.action_type_translations VALUES (3, -99, -97, 'Simulation', 'These Actions represent processes which run a simulation.', 'Simulation', 'Simulations', 'View Simulations', 'Run Simulation');
INSERT INTO public.action_type_translations VALUES (4, -98, -99, 'Probenerstellung', 'Diese Aktionen repräsentieren Prozesse, die Proben erstellen.', 'Probe', 'Proben', 'Proben anzeigen', 'Probe erstellen');
INSERT INTO public.action_type_translations VALUES (5, -98, -98, 'Messung', 'Diese Aktionen repräsentieren Prozesse, die Messungen durchführen.', 'Messung', 'Messungen', 'Messungen anzeigen', 'Messung durchführen');
INSERT INTO public.action_type_translations VALUES (6, -98, -97, 'Simulation', 'Diese Aktionen repräsentieren Prozesse, die Simulationen durchführen.', 'Simulation', 'Simulationen', 'Simulationen anzeigen', 'Simulation durchführen');

--
-- Data for Name: action_types; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.action_types VALUES (-99, false, true, true, true, true, true, true, true, true, true, false);
INSERT INTO public.action_types VALUES (-98, false, true, true, false, true, true, true, true, true, true, false);
INSERT INTO public.action_types VALUES (-97, false, true, true, false, true, true, true, true, true, true, false);


--
-- Data for Name: actions; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.actions VALUES (2, -99, NULL, '{"title": "Sample Information", "type": "object", "properties": {"name": {"title": {"en": "Sample Name"}, "type": "text", "default": "OMBE-", "minLength": 1, "maxLength": 100, "pattern": "^OMBE-[0-9]+$"}, "created": {"title": {"en": "Creation Datetime"}, "type": "datetime"}, "substrate": {"title": {"en": "Substrate"}, "type": "text", "minLength": 1, "dataverse_export": true}, "checkbox": {"title": {"en": "Checkbox"}, "type": "bool"}, "dropdown": {"title": {"en": "Dropdown"}, "type": "text", "choices": ["Option A", "Option B", "Option C"]}, "multilayer": {"title": {"en": "Multilayers"}, "type": "array", "minItems": 1, "items": {"title": "Multilayer", "type": "object", "properties": {"repetitions": {"title": "Film Layer Repetitions", "type": "quantity", "units": "1", "default": 1}, "films": {"title": "Films", "type": "array", "minItems": 1, "items": {"title": "Film", "type": "object", "properties": {"name": {"title": "Film Name", "type": "text", "minLength": 1}, "thickness": {"title": "Film Thickness", "type": "quantity", "units": "\u00c5"}, "oxygen_flow": {"title": "Oxygen Flow", "type": "quantity", "units": "sccm"}, "substrate_temperature": {"title": "Substrate Temperature", "type": "quantity", "units": "degC"}, "elements": {"title": "Elements", "type": "array", "style": "table", "minItems": 1, "items": {"title": "Element", "type": "object", "properties": {"name": {"title": "Element Name", "type": "text", "minLength": 1}, "frequency_change": {"title": "Frequency Change", "type": "quantity", "units": "Hz / s"}, "rate": {"title": "Rate", "type": "quantity", "units": "\u00c5 / s"}, "fraction": {"title": "Fraction", "type": "quantity", "units": "1"}}, "propertyOrder": ["name", "frequency_change", "fraction", "rate"]}}}, "propertyOrder": ["name", "thickness", "oxygen_flow", "substrate_temperature", "elements"]}}}, "propertyOrder": ["repetitions", "films"]}}}, "propertyOrder": ["name", "created", "checkbox", "dropdown", "substrate", "multilayer"], "required": ["name", "created", "checkbox", "substrate", "dropdown", "multilayer"], "displayProperties": ["substrate"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (3, -99, 1, '{"title": {"en": "Sample Information"}, "type": "object", "batch": true, "batch_name_format": "-{:03d}", "properties": {"name": {"title": {"en": "Sample Name"}, "type": "text", "default": "OMBE-", "minLength": 1, "maxLength": 100, "pattern": "^OMBE-[0-9]+-[0-9]+$"}, "created": {"title": {"en": "Creation Datetime"}, "type": "datetime"}, "substrate": {"title": {"en": "Substrate"}, "type": "text", "minLength": 1}, "checkbox": {"title": {"en": "Checkbox"}, "type": "bool"}, "dropdown": {"title": "Dropdown", "type": "text", "choices": ["Option A", "Option B", "Option C"]}, "multilayer": {"title": {"en": "Multilayers"}, "type": "array", "minItems": 1, "items": {"title": "Multilayer", "type": "object", "properties": {"repetitions": {"title": "Film Layer Repetitions", "type": "quantity", "units": "1", "default": 1}, "films": {"title": "Films", "type": "array", "minItems": 1, "items": {"title": "Film", "type": "object", "properties": {"name": {"title": "Film Name", "type": "text", "minLength": 1}, "thickness": {"title": "Film Thickness", "type": "quantity", "units": "\u00c5"}, "oxygen_flow": {"title": "Oxygen Flow", "type": "quantity", "units": "sccm"}, "substrate_temperature": {"title": "Substrate Temperature", "type": "quantity", "units": "degC"}, "elements": {"title": "Elements", "type": "array", "style": "table", "minItems": 1, "items": {"title": "Element", "type": "object", "properties": {"name": {"title": "Element Name", "type": "text", "minLength": 1}, "frequency_change": {"title": "Frequency Change", "type": "quantity", "units": "Hz / s"}, "rate": {"title": "Rate", "type": "quantity", "units": "\u00c5 / s"}, "fraction": {"title": "Fraction", "type": "quantity", "units": "1"}}, "propertyOrder": ["name", "frequency_change", "fraction", "rate"]}}}, "propertyOrder": ["name", "thickness", "oxygen_flow", "substrate_temperature", "elements"]}}}, "propertyOrder": ["repetitions", "films"]}}}, "propertyOrder": ["name", "created", "checkbox", "dropdown", "substrate", "multilayer"], "required": ["name", "created", "checkbox", "substrate", "dropdown", "multilayer"], "displayProperties": ["substrate"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (1, -99, 1, '{"title": {"en": "Sample Information"}, "type": "object", "properties": {"name": {"title": {"en": "Sample Name"}, "type": "text", "default": "OMBE-", "minLength": 1, "maxLength": 100, "pattern": "^OMBE-[0-9]+$"}, "created": {"title": {"en": "Creation Datetime"}, "type": "datetime"}, "sample": {"title": {"en": "Previous Sample"}, "type": "sample"}, "tags": {"title": {"en": "Tags"}, "type": "tags"}, "substrate": {"title": {"en": "Substrate"}, "type": "text", "minLength": 1}, "substratePreparation": {"title": {"en": "Substrate Preparation"}, "type": "text", "minLength": 0, "multiline": true}, "multilayer": {"title": {"en": "Multilayers"}, "type": "array", "minItems": 1, "items": {"title": "Multilayer", "type": "object", "properties": {"rateCalibration": {"title": "Rate Calibration", "type": "array", "style": "table", "minItems": 0, "items": {"title": "Element", "type": "object", "properties": {"timestamp": {"title": {"en": "Timestamp", "de": "Zeitstempel"}, "type": "datetime"}, "name": {"title": "Element Name", "type": "text", "minLength": 1}, "temperature": {"title": "Temperature", "type": "quantity", "units": "degC"}, "frequency_change": {"title": "Frequency Change", "type": "quantity", "units": "Hz / s"}, "rate": {"title": "Rate", "type": "quantity", "units": "\u00c5 / s"}, "comment": {"title": "Comment", "type": "text"}}, "propertyOrder": ["timestamp", "name", "temperature", "frequency_change", "rate", "comment"]}}, "repetitions": {"title": "Film Layer Repetitions", "type": "quantity", "units": "1", "default": 1}, "comment": {"title": "Comment", "type": "text", "minLength": 0, "multiline": true}, "films": {"title": "Films", "type": "array", "minItems": 1, "items": {"title": "Film", "type": "object", "properties": {"name": {"title": "Film Name", "type": "text", "minLength": 1}, "thickness": {"title": "Film Thickness", "type": "quantity", "units": "\u00c5"}, "deposition_time": {"title": "Deposition Time", "type": "quantity", "units": "s"}, "oxygen_flow": {"title": "Oxygen Flow", "type": "quantity", "units": "sccm"}, "substrate_temperature": {"title": "Substrate Temperature", "type": "quantity", "units": "degC"}, "annealing_temperature": {"title": "Annealing Temperature", "type": "quantity", "units": "degC"}, "annealing_time": {"title": "Annealing Time", "type": "quantity", "units": "s"}, "rateCalibration": {"title": "Rate Calibration", "type": "array", "style": "table", "minItems": 0, "items": {"title": "Element", "type": "object", "properties": {"timestamp": {"title": "Timestamp", "type": "datetime"}, "name": {"title": "Element Name", "type": "text", "minLength": 1}, "temperature": {"title": "Temperature", "type": "quantity", "units": "degC"}, "frequency_change": {"title": "Frequency Change", "type": "quantity", "units": "Hz / s"}, "rate": {"title": "Rate", "type": "quantity", "units": "\u00c5 / s"}, "comment": {"title": "Comment", "type": "text"}}, "propertyOrder": ["timestamp", "name", "temperature", "frequency_change", "rate", "comment"]}}, "comment": {"title": "Comment", "type": "text", "minLength": 0, "multiline": true}, "elements": {"title": "Elements", "type": "array", "style": "table", "minItems": 1, "items": {"title": "Element", "type": "object", "properties": {"name": {"title": "Element Name", "type": "text", "minLength": 1}, "temperature": {"title": "Temperature", "type": "quantity", "units": "degC"}, "frequency_change": {"title": "Frequency Change", "type": "quantity", "units": "Hz / s"}, "rate": {"title": "Rate", "type": "quantity", "units": "\u00c5 / s"}, "fraction": {"title": "Fraction", "type": "quantity", "units": "1"}, "comment": {"title": "Comment", "type": "text"}}, "propertyOrder": ["name", "temperature", "frequency_change", "fraction", "rate", "comment"]}}}, "propertyOrder": ["name", "thickness", "deposition_time", "oxygen_flow", "substrate_temperature", "annealing_temperature", "annealing_time", "comment", "rateCalibration", "elements"]}}}, "propertyOrder": ["repetitions", "comment", "rateCalibration", "films"]}}, "comment": {"title": "Comment", "type": "text", "minLength": 0, "multiline": true}}, "propertyOrder": ["sample", "name", "created", "tags", "substrate", "substratePreparation", "multilayer", "comment"], "required": ["name", "created", "substrate", "multilayer"], "displayProperties": ["tags", "substrate"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (4, -98, 2, '{"title": "Measurement Information", "type": "object", "properties": {"name": {"title": {"en": "English name", "de": "Deutscher Name"}, "type": "text", "default": "XRR-", "minLength": 1, "maxLength": 100, "pattern": "^XRR-[0-9]+$"}, "sample": {"title": {"en": "Sample"}, "type": "sample"}, "created": {"title": {"en": "Creation Datetime", "de": "Erstellungszeit"}, "type": "datetime"}, "slitWidth": {"title": {"en": "Slit Width"}, "type": "quantity", "units": "mm"}, "type": {"title": {"en": "Measurement Type"}, "type": "text", "choices": ["Rocking-Curve-Scan", "\u03c9-2\u03b8-Scan", "Z-Scan", "\u03c7-Scan"]}, "minRange": {"title": {"en": "Min. Range"}, "type": "quantity", "units": "1"}, "maxRange": {"title": "Max. Range", "type": "quantity", "units": "1"}, "stepSize": {"title": {"en": "Step Size"}, "type": "quantity", "units": "1"}, "stepTime": {"title": "Step Time", "type": "quantity", "units": "s"}, "temperature": {"title": "Temperature", "type": "quantity", "units": "degC", "default": 293.15}, "description": {"title": {"en": "Description", "de": "Beschreibung"}, "type": "text", "multiline": true, "default": ""}, "markdown_content": {"title": {"en": "Markdown", "de": "Markdown"}, "type": "text", "markdown": true, "default": ""}, "short_name": {"title": {"en": "Short name", "de": "kurzer Name"}, "type": "text", "default": "XRR-", "minLength": 1, "maxLength": 100, "pattern": "^XRR-[0-9]+$"}}, "propertyOrder": ["name", "short_name", "description", "markdown_content", "sample", "created", "slitWidth", "type", "minRange", "maxRange", "stepSize", "stepTime", "temperature"], "required": ["name", "sample", "created", "type"], "displayProperties": ["sample", "type", "description"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (5, -99, NULL, '{"title": "Minimal Object", "type": "object", "properties": {"name": {"title": "Object Name", "type": "text", "languages": "all"}, "tags": {"title": "Tags", "type": "tags"}, "mass": {"title": "Mass", "type": "quantity", "units": "kg"}}, "propertyOrder": ["name", "tags", "mass"], "required": ["name"], "displayProperties": ["tags", "mass"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (6, -98, 3, '{"title": "Measurement Information", "type": "object", "properties": {"data_file_name": {"title": "Data File Name", "type": "text", "default": "", "minLength": 0, "note": "optional"}, "sample": {"title": "Sample", "type": "sample"}, "created": {"title": "Creation Datetime", "type": "datetime"}, "name": {"title": "Sequence File Name", "type": "text", "minLength": 1}, "rso_magnetic_moment": {"title": "Option: RSO magnetic moment", "type": "bool"}, "dc_magnetic_moment": {"title": "Option: DC magnetic moment", "type": "bool"}, "ac_susceptibility": {"title": "Option: AC susceptibility", "type": "bool"}, "dc_oven_magnetic_moment": {"title": "Option: DC oven magnetic moment", "type": "bool"}, "dc_rotator_magnetic_moment": {"title": "Option: DC rotator magnetic moment", "type": "bool"}, "me_ac_susceptibility": {"title": "Option: ME AC susceptibility", "type": "bool"}, "ultra_low_field_option": {"title": "Option: Ultra-Low-Field option", "type": "bool"}, "service": {"title": "Option: Service", "type": "bool"}, "other_option": {"title": "Option: Other", "type": "text", "minLength": 0, "maxLength": 200}, "transport_unit": {"title": "Transport Unit", "type": "text", "choices": ["RSO head", "DC head"]}, "he_level": {"title": "He Level", "type": "quantity", "units": "percent", "note": "He Level must be always >50%"}, "straw_with_plateau": {"title": "Sample Holder: Straw with plateau", "type": "bool"}, "straw_with_gelatine_capsule": {"title": "Sample Holder: Straw with gelatine capsule", "type": "bool"}, "electrical_connection_sample_holder": {"title": "Sample Holder: Electrical connection sample holder", "type": "bool"}, "other_sample_holder": {"title": "Sample Holder: Other", "type": "text", "minLength": 0, "maxLength": 200}, "sample_description": {"title": "Sample Description", "type": "text", "minLength": 0, "multiline": true}, "measurement_description": {"title": "Measurement Description and Comments", "type": "text", "minLength": 0, "multiline": true}, "problems": {"title": "Technical Problems", "type": "text", "minLength": 0, "multiline": true}}, "propertyOrder": ["name", "data_file_name", "sample", "created", "rso_magnetic_moment", "dc_magnetic_moment", "ac_susceptibility", "dc_oven_magnetic_moment", "dc_rotator_magnetic_moment", "me_ac_susceptibility", "ultra_low_field_option", "service", "other_option", "transport_unit", "he_level", "straw_with_plateau", "straw_with_gelatine_capsule", "electrical_connection_sample_holder", "other_sample_holder", "sample_description", "measurement_description", "problems"], "required": ["sample", "created", "name", "transport_unit"], "displayProperties": ["sample"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (9, -99, NULL, '{"title": "Sample Information", "type": "object", "properties": {"name": {"title": "Sample Name", "type": "text", "default": "Sample-", "minLength": 1, "maxLength": 100, "pattern": "^.+$"}, "sample": {"title": "Previous Sample", "type": "sample"}, "created": {"title": "Creation Datetime", "type": "datetime"}, "tags": {"title": "Tags", "type": "tags"}, "description": {"title": "Description", "type": "text", "minLength": 0, "multiline": true}}, "propertyOrder": ["sample", "name", "created", "tags", "description"], "required": ["name", "created"], "displayProperties": ["tags"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (11, -98, NULL, '{"title": "Example Object", "type": "object", "properties": {"name": {"title": "Object Name", "type": "text", "languages": ["en", "de"]}, "sample": {"title": "Sample", "type": "sample"}, "comment": {"title": {"en": "Comment", "de": "Kommentar"}, "type": "text", "markdown": true, "languages": "all"}}, "required": ["name"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (12, -99, 5, '{"title": "Plotly Example Object", "type": "object", "properties": {"name": {"title": "Object Name", "type": "text"}, "plot1": {"title": "Example Plot 1", "type": "plotly_chart"}}, "propertyOrder": ["name", "plot1"], "required": ["name"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (14, -99, NULL, '{"title": "Example Object", "type": "object", "properties": {"name": {"title": "Object Name", "type": "text", "languages": ["en", "de"]}, "dropdown": {"title": {"en": "English Title", "de": "Deutscher Titel"}, "type": "text", "choices": [{"en": "en 1", "de": "de 1"}, {"en": "en 2", "de": "de 2"}, {"en": "en 3"}], "default": {"en": "en 2", "de": "de 2"}}, "user": {"title": {"en": "User", "de": "Nutzer"}, "type": "user"}, "conditional_text": {"title": "Conditional Name", "type": "text", "markdown": true, "conditions": [{"type": "choice_equals", "property_name": "dropdown", "choice": {"en": "en 1", "de": "de 1"}}, {"type": "user_equals", "property_name": "user", "user_id": null}]}}, "required": ["name"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (7, -98, 4, '{"title": "Measurement Information", "type": "object", "properties": {"name": {"title": "Measurement Name", "type": "text", "default": "", "minLength": 1, "maxLength": 100, "pattern": "^.+$"}, "created": {"title": "Creation Datetime", "type": "datetime"}, "keywords": {"title": "Keywords", "type": "text", "minLength": 0}, "sample": {"title": "Sample", "type": "sample"}, "geometry": {"title": "Geometry", "type": "text", "choices": ["Flat", "Capillary"]}, "diameter": {"title": "Diameter / Thickness", "type": "quantity", "units": "mm"}, "standards": {"title": "Standard Additives", "type": "text", "choices": ["SiO2", "LaB6", "Other"]}, "additives": {"title": "Other Additives", "type": "text", "minLength": 0, "multiline": true}, "wavelength": {"title": "Wavelength", "type": "text", "choices": ["1.54 \u00c5", "0.71 \u00c5"], "default": "1.54 \u00c5"}, "options": {"title": "Options", "type": "text", "choices": ["None", "Closed-Cycle Cryostat", "Laser Heating Module", "Cryo-heating Module", "High Pressure Cell"], "default": "None"}, "temperatures": {"title": "Temperatures", "type": "array", "minItems": 1, "maxItems": 50, "style": "table", "items": {"title": "Temperature", "type": "object", "properties": {"temperature": {"title": "Temperature", "type": "quantity", "units": "K"}}, "required": ["temperature"]}}, "pressure": {"title": "Pressure", "type": "quantity", "units": "GPa"}, "duration": {"title": "Duration", "type": "quantity", "units": "min"}, "scans": {"title": "Number of Detector Scans", "type": "quantity", "units": "1"}}, "propertyOrder": ["name", "created", "keywords", "sample", "geometry", "diameter", "standards", "additives", "wavelength", "options", "temperatures", "pressure", "duration", "scans"], "required": ["name", "sample", "created", "wavelength", "geometry", "diameter", "additives", "standards", "duration", "temperatures", "pressure", "scans"], "displayProperties": ["sample", "keywords"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (8, -98, 5, '{"title": "Measurement Information", "type": "object", "properties": {"sample": {"title": "Sample", "type": "sample"}, "name": {"title": {"en": "Measurement Name", "de": "Messungsname"}, "type": "text", "default": "GALAXI-", "minLength": 1, "maxLength": 1000, "pattern": "^GALAXI-.+_[0-9]+$"}, "created": {"title": {"en": "Creation Datetime", "de": "Erstellungsdatum"}, "type": "datetime"}, "tags": {"title": "Tags", "type": "tags"}, "measurement_type": {"title": {"en": "Measurement Type", "de": "Messungstyp"}, "type": "text", "choices": ["SAXS", "GISAXS", "Reflectometry"]}, "temperature": {"title": {"en": "Temperature"}, "type": "quantity", "units": "degC", "default": 298.15}, "magnetic_field": {"title": {"en": "Magnetic Field"}, "type": "quantity", "units": "mT", "default": 0}, "beam_center_x": {"title": {"en": "Beam Center (X)"}, "type": "quantity", "units": "1"}, "beam_center_y": {"title": {"en": "Beam Center (Y)"}, "type": "quantity", "units": "1"}, "detector_z": {"title": {"en": "Detector Z"}, "type": "quantity", "units": "mm"}, "sample_detector_distance": {"title": {"en": "Sample to Detector Distance"}, "type": "quantity", "units": "mm"}, "comment": {"title": {"en": "Comment"}, "type": "text", "minLength": 0, "multiline": true}}, "propertyOrder": ["sample", "name", "created", "tags", "measurement_type", "temperature", "magnetic_field", "beam_center_x", "beam_center_y", "detector_z", "sample_detector_distance", "comment"], "required": ["sample", "name", "created", "measurement_type", "temperature", "magnetic_field"], "displayProperties": ["tags"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (10, -99, NULL, '{"title": "Example Object", "type": "object", "properties": {"name": {"title": {"en": "Object Name", "de": "Objektname"}, "type": "text", "languages": "all"}, "sample": {"title": {"en": "Sample", "de": "Probe"}, "type": "sample"}}, "required": ["name"]}', NULL, false, false, false);
INSERT INTO public.actions VALUES (13, -99, NULL, '{"title": "Plotly Array Example Object", "type": "object", "properties": {"name": {"title": "Object Name", "type": "text"}, "plotlist": {"title": "Plot List", "type": "array", "style": "list", "minItems": 1, "items": {"title": "listitem", "type": "plotly_chart"}}}, "propertyOrder": ["name", "plotlist"], "required": ["name"]}', NULL, false, false, false);


--
-- Data for Name: api_log_entries; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: association; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.association VALUES (1, 2);
INSERT INTO public.association VALUES (2, 2);
INSERT INTO public.association VALUES (3, 2);
INSERT INTO public.association VALUES (4, 2);
INSERT INTO public.association VALUES (5, 2);


--
-- Data for Name: authentications; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.authentications VALUES (1, 1, '{"login": "admin", "bcrypt_hash": "$2b$12$9M3j5rEZqE0eZmVgl8amhew/nM.apFgApClMfANfTuw1vFRrqR.KW"}', 'OTHER', true);
INSERT INTO public.authentications VALUES (2, 4, '{"login": "api", "bcrypt_hash": "$2b$12$tmBxC4QGkS2w2j1TyEoFXujnp6zjpT292f51wE/ex4h2nc.MUQ7Xa"}', 'OTHER', true);


--
-- Data for Name: comments; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.comments VALUES (1, 1, 2, 'This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. This comment is very long. 
This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. 

This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. This comment has three paragraphs. ', '2021-07-02 08:29:28.420862');
INSERT INTO public.comments VALUES (2, 1, 2, 'This is another, shorter comment', '2021-07-02 08:29:28.433443');


--
-- Data for Name: dataverse_exports; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: default_group_permissions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: default_project_permissions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: default_public_permissions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: default_user_permissions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: favorite_actions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: favorite_instruments; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: file_log_entries; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.file_log_entries VALUES (1, 'EDIT_TITLE', 1, 1, 2, '{"title": "Example File"}', '2021-07-02 08:29:28.475865');
INSERT INTO public.file_log_entries VALUES (2, 'EDIT_DESCRIPTION', 1, 1, 2, '{"description": "This is a file description."}', '2021-07-02 08:29:28.481121');


--
-- Data for Name: files; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.files VALUES (0, 1, 2, '2021-07-02 08:29:28.445431', '{"storage": "local", "original_file_name": "example.txt"}');
INSERT INTO public.files VALUES (1, 1, 2, '2021-07-02 08:29:28.45953', '{"storage": "local", "original_file_name": "demo.png"}');
INSERT INTO public.files VALUES (2, 1, 2, '2021-07-02 08:29:28.486416', '{"storage": "url", "url": "http://iffsamples.fz-juelich.de/"}');


--
-- Data for Name: group_action_permissions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: group_invitations; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: group_object_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.group_object_permissions VALUES (2, 1, 'READ');
INSERT INTO public.group_object_permissions VALUES (3, 1, 'READ');
INSERT INTO public.group_object_permissions VALUES (4, 1, 'READ');


--
-- Data for Name: group_project_permissions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: groups; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.groups VALUES (1, '{"en": "Example Group", "de": "Beispielgruppe"}', '{"en": "This is an example group for testing purposes.", "de": "Dies ist eine Beispielgruppe f\u00fcr Testzwecke"}');


--
-- Data for Name: instrument_log_categories; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.instrument_log_categories VALUES (1, 1, 'Error', 'RED');
INSERT INTO public.instrument_log_categories VALUES (2, 1, 'Warning', 'YELLOW');
INSERT INTO public.instrument_log_categories VALUES (3, 1, 'Success', 'GREEN');
INSERT INTO public.instrument_log_categories VALUES (4, 1, 'Other', 'BLUE');
INSERT INTO public.instrument_log_categories VALUES (5, 1, 'Normal', 'GRAY');


--
-- Data for Name: instrument_log_entries; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.instrument_log_entries VALUES (1, 1, 3);
INSERT INTO public.instrument_log_entries VALUES (2, 1, 3);
INSERT INTO public.instrument_log_entries VALUES (3, 1, 3);
INSERT INTO public.instrument_log_entries VALUES (4, 1, 3);
INSERT INTO public.instrument_log_entries VALUES (5, 1, 3);
INSERT INTO public.instrument_log_entries VALUES (6, 1, 3);
INSERT INTO public.instrument_log_entries VALUES (7, 1, 3);
INSERT INTO public.instrument_log_entries VALUES (8, 1, 3);


--
-- Data for Name: instrument_log_entry_version_category_associations; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.instrument_log_entry_version_category_associations VALUES (1, 1, 1);
INSERT INTO public.instrument_log_entry_version_category_associations VALUES (2, 1, 2);
INSERT INTO public.instrument_log_entry_version_category_associations VALUES (3, 1, 3);
INSERT INTO public.instrument_log_entry_version_category_associations VALUES (4, 1, 4);
INSERT INTO public.instrument_log_entry_version_category_associations VALUES (5, 1, 5);
INSERT INTO public.instrument_log_entry_version_category_associations VALUES (7, 1, 4);
INSERT INTO public.instrument_log_entry_version_category_associations VALUES (8, 1, 1);
INSERT INTO public.instrument_log_entry_version_category_associations VALUES (8, 1, 2);
INSERT INTO public.instrument_log_entry_version_category_associations VALUES (8, 1, 3);
INSERT INTO public.instrument_log_entry_version_category_associations VALUES (8, 1, 5);


--
-- Data for Name: instrument_log_entry_versions; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.instrument_log_entry_versions VALUES (1, 1, 'This is an example instrument log entry', '2021-07-02 08:29:27.92518', false, NULL);
INSERT INTO public.instrument_log_entry_versions VALUES (2, 1, 'This is an example instrument log entry', '2021-07-02 08:29:27.961868', false, NULL);
INSERT INTO public.instrument_log_entry_versions VALUES (3, 1, 'This is an example instrument log entry', '2021-07-02 08:29:27.983697', false, NULL);
INSERT INTO public.instrument_log_entry_versions VALUES (4, 1, 'This is an example instrument log entry', '2021-07-02 08:29:28.005272', false, NULL);
INSERT INTO public.instrument_log_entry_versions VALUES (5, 1, 'This is an example instrument log entry', '2021-07-02 08:29:28.026313', false, NULL);
INSERT INTO public.instrument_log_entry_versions VALUES (6, 1, 'This is an example instrument log entry', '2021-07-02 08:29:28.046033', false, NULL);
INSERT INTO public.instrument_log_entry_versions VALUES (7, 1, 'This is an example instrument log entry', '2021-07-02 08:29:28.065347', false, NULL);
INSERT INTO public.instrument_log_entry_versions VALUES (8, 1, 'This is an example instrument log entry', '2021-07-02 08:29:28.088721', false, NULL);


--
-- Data for Name: instrument_log_file_attachments; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.instrument_log_file_attachments VALUES (1, 8, 'ghs01.png', '\x89504e470d0a1a0a0000000d49484452000000f0000000f008060000003e55e99200000006624b474400ff00ff00ffa0bda7930000000774494d4507da0b13033700d84c42e40000200049444154789ceddd775c1477fec7f137ecd255b0a08805458c0d822d2a448da289ddd368124b881a2b89b144a326c6ae89dd534f3d6b4cec9e35267a3f1514492c492c410151b0008a20d27797b2ece7f707618e0d0b2c30db3fcfc7631ff1d8d999ef72bc766667676601c618638c31262202ea13e068e87130c62a888086043c20e02247cc980929162ffd75e3881933051ae2e58819330565c45b740be6881933425ac4cb1133668c2a102f47cc9831f92bde871588972366cc1854215e8e98314312215e8e98314310315e8e98317dd241bc1c3163faa0c3783962c674490ff172c48ce9821ee3e58819139301e2e58819138301e32dba8570c48c558211c4cb113356197fc51b6304f172c48c5584a8f18e1943f4e69b1c3163fa206abce3c61129954499991c3163baa693788b70c48ce98e4ee3e58819d31dbdc4cb1133263ebdc6cb1133261e83c45b3ce2ae5d3962c62ac3a0f172c48c559e51c4ab9b882f71c4ccac891e6f4141e5e3e58819d31e018d8c2e5e8e98b1f21975bc1c3163a53389783962c64a32a9783962c6fec724e32d9295c51133cb65d2f172c4cc929945bc1c31b34466152f47cc2c8959c65b842366e64cd4783ffed8b8e22dc21133736411f116e1889939b1a8788b881bf1658e98198445c65b242b8ba85b378e9899a6bfe28db5c8788b70c4cc1471bcc570c4cc9470bc1a70c4cc1470bc65e0889931e378b5c0113363c4f1560047cc8c89e8f1aa54864e4cf73862660c38de2ae088992171bc22c8cee68899fe71bc221237e2508e989589e3d5018e98e903018d395e1de188992e71bc440a8542b70be088992e70bc853a76ec4823478ea43b77eee86e211c311313c75b282222820a7f1d202b2b2bdab66d9bee16c611333170bcff337ffe7c216000ba5d0b1371c4ac6a448d77fc78938e57a55291a7a7a710af8f8f8f7e169c9d4dd4bd3b47cc2a86e35577f5ea55b5b5efb7df7eabbf8573c4ac2238de92a64f9f2ec46b6d6d4d717171fa1d0047ccb4c1f196a4542ac9cdcd4d08f8adb7de32cc40386256168e57b3f3e7cfab6d3eefd8b1c37083e18899261c6fe9c68e1d2bc46b676747696969861d1047cc8ae3784ba75028a8468d1a42c043870e35f4900a71c40ce078cb73ecd831b5cde713274e187a48ffc3115b368eb77cc3870f17e2757171a19c9c1c430f491d476c99448d77c204b38c37232383eceded8580274e9c68e82169269371c49684e3d5ce77df7da7b6f97cf9f265430fa9741cb165e078b5f7f6db6f0bf1366ad4880a8cfd4a991cb179e378cb161a1a4ab9b9b94444949898481289440878debc793a5df6ac59b3e8cb2fbf2455557fa71cb179e278cbe7eeee4e2d5bb6a4949414dabc79b3dae6737878b8ce96fbedb7df0acbd9b97367d567c8119b178eb7a48c8c0c616d4b441415154500a85ebd7a545050407e7e7e4254bebebe3a1bc78e1d3bc8caca8a0050fffefdd5c654251cb179e0784b4a4a4a225b5b5b0240376fde2422a2ad5bb712009a346912c5c6c60a5101a0d5ab57eb641ca74e9d1236d3fbf6ed2b5ebc453862d3266abc66f0396f646424eddfbf9f962c5922c4b960c10222fadfe7bdfffdef7f69f9f2e5c2fdd6d6d6141f1f2ffa588283838517913e7dfae8ee5a5b1cb169e2784b5ab76e9d1066d1cdd7d797542a15d5a953875c5c5c282f2f8f5ab76e2ddc1f101020fa387efffd777276762600f4f6db6f935c2e177d196a3862d3c2f16a3662c488120103a053a74e11000a0c0ca4f0f070b5fb76edda25ea181e3e7c48aeaeae04807af5ea4532994cd4f9978a23360d1c6fe9bcbcbc4ac46b6b6b4b63c68c21a0f038e779f3e609f7d9dbdb5346468668cb8f8f8f270f0f0f02403d7af4d05fbc453862e3c6f196ed9b6fbea15ab56a09815a5959d1fefdfb69d0a041e4e4e44432994c080c000d1f3e5cedf16bd7aea5ddbb7757eab3da57af5e918f8f0f01a0eeddbbeb3fde221cb171e278b573e5ca1521d0cd9b379352a9241717171a366c18858585a9ad9d4f9d3a253ceed5ab5754a3460d727474a4e7cf9f57689932998c3a77ee4c00a85bb76e949d9d2df6d3aa188ed8b870bcda532a95e4ecec4c1f7ef8211111fdf6db6f04800e1c384041414142bcb56ad552fb58e7abafbe2200b474e9d20a2d2f373797faf6ed4b00e8cd37dfa4cccc4c519f4fa571c4c681e3adb8b973e70a21ad5ab58aececec28252585ead4a923043c79f26461fae4e464aa5ebd3a356edcb8429bbe2a958a468f1e4d00c8dfdf5fd4f7d3a2e0880d8be3ad9ce2ef61fbf4e94303060ca073e7cea96d3e87858509d3cc99338700d0e1c3872bb49c4f3ef9840050e7ce9d293d3d5db4f197e6e5cb97157f10476c181c6fd5e5e5e591939313eddebd9b02030385789b366d2a449e9494444e4e4ed4ad5bb70aedbc5aba742901a037de78432ff11215be183d7dfab4e20fe488f58be315475858184924127afaf42955af5e5d0878fefcf9c234b367cf266b6b6bfae38f3f888868c58a15f4c30f3f50545454a9f32d3a2cb343870e7a8b37313191acadade9bdf7deabdc0cf8ca1efac1f18a67d9b26514101040870f1f56db7c8e8c8c24a2c2281c1c1c68fcf8f1444474f2e449619a3973e6689ce7c1830749229150fbf6ed293535556fcf65dbb66dc2d84242422a37138e58b7385e71f5e8d183366fde4c83070f16fef83b74e820dc3f7dfa74aa51a3062526261211d1471f7d244ce7e1e151627e172f5e245b5b5b6adbb62dbd7af5aac2e3c9c8c8a04b972e55eab9f4ead54b189bb7b737e5e7e7576a3e1cb18e70bce2522814e4e0e040e1e1e1c249050068c3860d4444f4ecd933727070a055ab56098f69d3a68d30dd1b6fbca136bfebd7af93a3a323f9fafa566a67d2952b57c8c3c343ab0b07fcf1c71fd4be7d7b727777178ea9fefb6dcb962d151e8380231617c72bbee0e060ead2a50beddcb953f8a3974824c2daf6b3cf3ea3e6cd9b0b57a12c2828508b65dab469c2bc222222c8d5d5957c7c7c283939b942e3c8cbcba379f3e609a7156a1370f7eedd35465bfc366ad4a80a8da3048e581c1caf6ecc9f3f9f56af5e4d010101c21f7d9f3e7d88a8f098653b3b3b3a79f2a4da63ae5ebd4ab56bd7a6162d5a083ba7e2e3e3a961c386d4a64d9b0ac71b1919491d3a7410966f656545dbb76f2ff771f5ead5d37dc0441c715571bcbae3efef4f57ae5c216b6b6be18ffe871f7e2022a2a0a020eaddbbb7c6c7c5c4c4d0c3870f89a8f0008f56ad5a51ebd6ad29292949eb65ab542adaba752b393a3a0acbf6f6f656fbecb9346969692562f5f1f1517b7f0eb10226e2882b8be3d59dacac2c7ae38d37d4ce0f767272a2acac2c7af2e409393a3ad2ddbb77cb9c47d1f1cd2d5bb61436bbb5f1e2c50beadfbfbfb05c070707faf6db6fb5be1a8742a1a0f9f3e79383830301202f2f2fe1d8ecd3a74f0bdfa2285ac0441c714571bcba75f6ec595ab26489dae66bd11ffcc48913d5dedf6a929b9b4b010101d4a2458b0a9dd870faf469aa5bb7aeb0cc7efdfa516c6c6ca59ec3d3a74f69f2e4c9f4e4c913b59fbf7af58a468c18216ec0441cb1b6385edd9b33670e1d3f7e5c6d93f3ecd9b3141b1b4b6e6e6e94929252ea63954a258d1831829a376f4ecf9e3dd36a79d9d9d93469d2246159f5ebd7a7a3478f8af574348a8989117fa61c71d9385efd183972242d5cb85008aa6eddba949f9f4f63c68ca1ad5bb796f9d8a0a020f2f2f2d2fa3a59376edca0d75e7b8d80c2eb6b4d9d3a556f4767e90447ac19c7ab1fa9a9a9347ffe7c6ad1a28510f0b469d3283a3a9a3a76ec484aa5b2d4c72e58b0809a356ba655bcf9f9f9b46cd932924aa50480dab76f4fbffdf69b984fc5703862751caffe9c3a754aedb0430074e3c60d1a3d7a749987206eddba959a366daad5c902b1b1b1e4efef4f00a85ab56ab461c386528f8caaf23731180a475c88e3d5af356bd6d0cc993385785f7bed358a8888a00f3ef8a0d4c7ecdfbf9f9a366daab6c3e8e6cd9bc231d3c5edd9b347f842f021438694b9b696c964d4b3674f3a72e448d59e5425a4a7a7d3e9d3a7cb3c29a35c961e31c7ab7f3b76ec2077777721e0254b96d0d8b1634b5db3fedffffd1f797a7ad2a3478f849f1d397284060f1eac365d4a4a8a706d690f0f0ffaf1c71fcb1d4bd1f41289a4c2e71a57944c26a3f3e7cfd3bc79f3a853a74ec2915f43860ca9da8c2d35628e57ff92939369f1e2c542bc56565674f2e4495abc78b1c6e9af5fbf4e1e1e1e74fffe7d222adcdc5db06001492412ba75eb9630ddf9f3e7c9dddd9da45229cd9e3d9bb2b2b2ca1d4b7474b4da66bc442211754d9c979747616161b478f1627aebadb7c8cece4e6d7900a871e3c6346ad4a8aa5f97dad222e6780de3f2e5cb346edc38e10fd8cfcf8fa64d9ba6f13239e1e1e1e4eaea4a93274fa6eddbb7d3962d5b68e0c0810440b89e9642a1a01933669095951575e9d285fefcf34fadc772fcf871ead4a99370e00500924aa5f49ffffca752cfada0a080fef8e30f5abd7a35f5eddb979c9c9cd462b5b1b1a1ce9d3bd38c1933e8e8d1a394909050a9e594cac823b6126b46043406700980679567367e3cb073276025daf04c5a5252126edcb881e8e868a8542a0080a3a323dab66d8b76edda212222027dfbf6457a7a3a0060fcf8f1e8dbb72f860f1fae369fd8d858f4e8d1030909092596616f6f8ffbf7ef23333313a3478f467c7c3c56ae5c89891327c2dadaba52e3cecdcd455c5c1ce2e2e29098988877df7d178e8ee5fffd46464622383818972e5dc2e5cb9791969626dce7eaea0a3f3f3ff8fbfbc3dfdf1f1d3b7684838343a5c6a735990ce8df1fb872458cb95d01d0cf0a908b313351f09a577c32998c76eedc491d3b762cb18958fc269148d4aef96c6363a3f1a4fc3d7bf6a85d9da3f8cdd9d999ce9c3943ebd6ad233b3b3b1a356a54a987512a140adab66d1bedddbb57b4e7fae8d123dab56b178d1a354a6dcd6d6d6d4ddedede3469d224dabb772f4547478bb6cc0a33f23571a571bce23b73e60c3569d2a4cc704bbbd5ae5d5bed7d2c51e10eaea2fba552a9da6668ab56ad282424847af7ee4dcd9b37a70b172e681c53464606ad5ab54a086cca9429957e7ecf9f3fa703070ed0f8f1e3a969d3a6c258aa57af4ebd7bf7a6850b17d2b973e78cefc010738b98e31557414101cd9831a352e116bf0d1e3c58b8bc6c6e6e2e8d1a358adcdddde9abafbea2f8f8789a356b1601a0418306d1eeddbbc9dddd9d162d5aa4f19b0493929268fefcf9e4e2e24240e185f1962e5d4a7171715a3fafd4d4543a71e2044d9d3a55ed0bd63c3d3de9c30f3fa42d5bb6d09d3b77ca3cd8442cb9b9b974e7ce1d3a78f06089173aad984bc41cafb8944aa5f0f18b18b7366dda507474344d983081222323d5e2b874e9124d9f3e9dc68c19430101011a374d1f3f7e4c9f7efa2939383890bdbd3d8d1e3d9a2e5cb840050505e53e97acac2c3a77ee1c7df1c517d4a14307b2b6b6263b3b3bf2f7f7a759b366d18913272a74a65365e4e5e5514444041d3d7a94162e5c48c3870fa7962d5b0a47900128f7f0d252997ac41caff88a7f7b8258371b1b1bfaf9e79f4b2cebead5abe4e7e7473ffcf0438923a6eeddbb4781818124954aa943870eb479f3e672af83959b9b4b972f5fa6458b1651d7ae5dc9c6c686dcdcdc68e8d0a1b476ed5afaf5d75f852b80884da954d283070fe8f8f1e3b47cf972fae0830fc8c7c747ed7242a5dd2a1d3091d1445ce1ddbcc47b9b45b777ef5e8c1b37aecaf371777747fdfaf5010031313170777747efdebdb169d326008052a9c48a152b909c9c8ce5cb97a366cd9ac263af5fbf8e952b57e2975f7ec1c891233176ec5874e8d041e3720a0a0a70fbf66d04070723242404d7ae5d83a7a727de7cf34d610fb1a767d5ff3c8a23223c7efc18111111888c8cc4bd7bf710111181a8a828e4e4e494fa387b7b7b787a7aa259b36668d6ac99dabf9b3469023b3bbbca0fca08f64e57a81c8eb7728808df7fff3d020303219148d4ee4b4e4e468b162d848f80aae2d0a143183162040e1c38005f5f5f787b7b0bf7c5c6c662f5ead51833660cfcfdfd859f9f3f7f1eab56ad82b5b535c68e1d8b61c386c1dedebec4bc8b3eda090909c19d3b77d0b2654b21d6ce9d3ba37af5ea551e7f91b8b83821d2e2ff95c9641aa7af53a78ec6403d3d3dd1a04103d1c6a5918123d6ba1e8eb76a7efae927ecdebd1bfffad7bfd4fea866ce9c897ffef39fa22c233131117ffef927dcdddde1e3e323fcfcf0e1c3484b4bc3c4891321954aa152a970f2e4491c3c78106ddab4c1d8b1634bac319f3c7982909010040707232121014d9b36153e7b6dddba75a53f1bfefb78232222845b51a81919196ad349a552346ad4a8d4486bd4a851e5b154890123d6aa208eb772626262e0e5e525fceff8f8787cf5d55718397224faf7ef8facac2cd4af5fbfd4354b59de7fff7d6cd8b001cf9e3dc38b172f909999094f4f4f383b3ba375ebd6008057af5ee1cc9933e8d9b3273c3c3c909f9f8f63c78e212a2a0a7e7e7ee8d3a78f106252521242424270fdfa75646464c0cdcd0dfefefef0f3f383abab6b957e0f292929429c77efde15d6aaa9a9a9c234d5aa55d3b8a9ebe9e9090f0f0fd8d8d854690c3a67a088cbad88e3adbcd3a74fe3e2c58b983061027c7d7d01146e4e6fd9b20589898968d4a8118282822a356f3b3b3b3c7bf60cb56bd706003c78f0002a950a2d5bb60400e1a8aa4e9d3a412e97e3c68d1b484d4d458f1e3d50bb766d64646420343414d1d1d150281470767646972e5dd0be7dfb4ac7929696a6b6462d5aab2627270300dcdcdc84408be22c0ab55ebd7a955aa6513140c46596c4f1569d52a9c4d1a347f1f8f1638c183102cd9a35030084878763d8b061888989a9f4bc376fde8ca953a7223e3e1e4aa5124d9b368552a9446262226ad5aa05272727bc7cf91272b91c75ebd6c58d1b3790929282dcdc5cd8d8d8a04b972e68dcb87185979b999989a8a828b5b569646424929393d1a4499352771a697318a5c9d373c4a5d6c4f18a4ba552e1a79f7e42727232060c1880faf5eb0b9bb27f7fcfa7ad418306e1c0810390c9647073730350f88221954aa1542a11131303854201b95c0e8944021f1f1f383939693d7f994c86a8a828b59d49cf9e3d83542ad51869a3468d4aeca4b3487a8c5863511caff60a0a0a306bd62c242727c3cfcf0f9d3b7746bb76ed4add0c2522848686422693e1cd37df446464243efcf043e4e6e6c2dddd1db56ad582b3b3336ad4a881d0d0d052d7d0aeaeae080d0d85bbbb3b9c9d9d4144c8cfcf875c2e476e6e2ef2f2f2d0b061435869f17bcfc9c94154541422232311111181b4b434e4e4e4402291a04993266aa1d6a95347edb97cf9e597484e4ec6cc9933d5769c593c3d455ce2ff5d8eb762d2d2d2101c1c8ce8e868dcbf7f1ff7efdf475c5c1c5ab46821ecb52d6d47d0bd7bf74044f0f2f2829d9d1deedebd8b66cd9aa15ab56a000ad7a6fbf7efc7b265cbf0e8d123e171b6b6b63877ee1c0202022a34d6bcbc3c44474723363616d9d9d9c8cbcb1376a01585eae9e9a9f163a4bf2b2828c0e4c993b17bf76e00809595157af5ea8559b366a14f9f3e5abd70983d3d44acf65be678c593909080fbf7efe3c18307888c8c0411a156ad5a68d4a851898f6292939321954ae1e2e202a552095b5b5bb5791585fccd37dfe0e1c387d8b97327264c98a071b9172f5e448f1e3df0ead52b28140ae4e4e42027270772b91c4484c68d1ba341830695fe1828313111c78e1dc381030770e3c60d8dd3b46edd1a3366cc406060a0562f06664dc7110b755952bcbffcf20b3ef9e413d8dbdbc3c5c5052e2e2ea859b3a6da7f35fdac66cd9a25368d8383834144a859b326bcbcbce0ecec5ce6b2b3b3b3111d1d8d172f5ec0d9d919b56bd716369b6d6d6d4b8495959585193366e0f3cf3f47cb962d71edda3574eddab5d4f9b76ad50a5dba74c1f6eddb4bbc1054d5c99327f1de7befa1a0a040abe9ebd6ad8ba0a0202c58b0c0b2df1beb306269b13becffba559d545afe3406d4b56b57fcf2cb2f48494911d652e9e9e9c8cbcb43767636643219323333f1f4e953e4e4e440a15020232303393939b0b2b2824422818383039e3e7d8a1f7ffc5198ef3befbc83a143870228fce3ad5fbfbe5afc767676a856ad9ac6431489a8c46667424202060c1880f0f0701c3f7e1c478f1ec53befbc53e67393cbe5d8bb772fe2e3e371f2e449518f906ad9b2a5d6f102855b16f6f6f6961d2f50b82213ef736cc95fb7c25917bf8780d750b81676aff262264f06b66d33dab57055e5e4e4a0458b16888b8b137e666d6d0d676767a4a5a5e1bbefbe43f7eedd919b9b0bb95c0e994c06a9540a2b2b2b54af5e1d1289046bd6ac41d3a64d3178f060787b7babfda1dfbe7d1b03070ec4f3e7cf859fd9d8d860ebd6adc2e6734141018808d2bf5e30af5dbb8677de7907d9d9d900803e7dfae0d0a143b0b6b6865c2e87542a4556561680c2bde20a85024484dcdc5c61cdefe2e2228c512a95c2d1d151385e988850b76e5da4a4a4c0cdcd0d7dfbf6457878386eddbaa5f177f4f1c71f0bef912d965c0e0c1e0c04078b31b75f51b8f6cd2afa81a69d58161db15c2e475e5e1e5c5c5cca9c2e3e3e1e6fbffd36a2a3a335de5fd6fbd42243860cc1e9d3a701009e9e9ee8d5ab97b0636ae2c48942887ff7c5175f60e5ca95b0b6b6466a6a2a525353b16ddb366cdcb8b1c41a32303010e3c68d438f1e3dcaddb194999909854201994c86f4f474c8e572c8e572646464203f3f1f00f0fcf973646464a071e3c650a954484a4ac2912347f0f0e143611a00a855ab16c68d1b075b5b5be16d45d1c913452f12cececeb0b6b6468d1a3520914884170d272727d8dadac2c1c1c1b4df43eb385ea0f48f912c32e27bf7ee61c48811c8cdcdc5f1e3c7f1faebaf9739bd5c2ec7b469d3d4d63273e7cec5a4499350a74e1d8dc7e8a6a7a7e3d5ab57904aa5f8f7bfff8d952b57566aac43870ec5be7dfbf0fbefbfe3e38f3fc6e3c78f4b9dd6d6d616c9c9c9e5be3fafaaecec6ca4a5a521353515afbdf61a1c1c1c841d68e9e9e9c8cece865c2e47767636323232842d938c8c0c8df7153d4ea954c2caca0a7279e1be1b954a253c97a21783a21701272727b8babae2ebafbf36ec31d27a881728fb400e8b8af8ead5abe8ddbb37140a0500c0c9c909bb76edc2881123ca7dece3c78f11151585888808f4ebd70f494949502a95904824b0b5b5859d9d1d2412096c6c6c84f7c640e1f1c70d1a34a8d0fbcae23c3c3c10171707222a77badebd7bab7da6ebe5e5855ab56a556ab98656f4f15751e80a850269696942f499999968d8b021faf7ef6f9801ea295ea0fc43292d26e2e8e868ecdab50bc9c9c9484a4a42626222929393111818886fbef90640e14728717171888f8f173efab1b6b616222d7e40bea6c3066532196edebc89d4d454d8d8d8402e9763c58a15f8f3cf3f75fadcc2c2c2e0ebeb8bd0d0505cba7409212121080f0f878b8b0bbcbcbc845bf3e6cd857f173f608355801ee305b43b99c122227ef9f225e2e3e391909080a74f9f222e2e0e0a8502128944787fd6b87163e16087860d1b96fb596a6c6cac70768f9d9d1d1c1d1d4144c249e879797968d0a001162c5880bcbc3c9d3cafa64d9be2f2e5cb258e797ef5ea152e5dba848b172f222424040f1f3e54bbdfc5c5456d6d5d3cf2a2c336d9dfe8395e40fbd309c58b78ca1460eb56bd462c97cb8528131212101f1f8fb8b8383c7ffe1c565656b0b1b141fdfaf54b9c215391f78c32990cbffffe3bae5fbf8eecec6cd8d9d9a155ab56a851a306eedebd8b4b972ec1dada1afdfbf747fbf6ed111f1f8f76eddac1d3d313ebd7afc7ac59b3447fde5656563871e204542a15e2e2e23076ecd8123be776edda857af5eac1d9d919070f1ec4f6eddbcb9d6fb56ad5d4a22e7e737777b7cca3b00c102f50b113fa8d36e2949414dcbf7f1f4f9f3e15d6a2451714cfc8c8808b8b8bdaf9a545ff6ddcb871a54f9d7bf0e001ae5dbb869b376f222b2b0bb56bd746b76eddf0faebafe3e2c58b080e0e46585818bcbdbdf1de7bef61c89021904aa53876ec189a356b869e3d7b0af32222b46cd9120f1e3c10e5f70114c6bb6fdf3e646767c3d6d61643870ec5a64d9b50b3664d4c9e3c19b6b6b6f8f9e79f3170e0c032e7e3e6e606954a259c12589ec3870fe3830f3e10e329980e03c55b6104bc46c033512ee435658a6817b35bbe7c39bdf5d65b346edc385ab66c191d3c7890ae5fbf4e2f5fbe1465fe99999914121242cb972fa77ffce31fd4af5f3f9a3d7b369d397386d2d2d2d4a6bd70e1020d183080befbee3b4a4d4d25a2c28bbe6ddfbe9d76ecd841b9b9b96ad32b140a5ab06001fdfaebafd4a54b17512e66676565450b162ca07dfbf6514e4e0e5db972853efdf4534a4b4ba39b376fd2a851a3e8d0a14374fbf66de14bbacbbaf9f9f9d1afbffe4a1b376ea4a1438752cd9a354b9df6f6eddba2fcce4d864c46d4ab975817b7fb8500f18ebc31a588c5141d1d4d7bf7eea5a0a020ead8b12375edda95e6cd9b4767cf9ea5cccc4cdabe7d3bcd9c3993162e5c486bd6ac29f54bbf542a151d3a7488befaea2b7af6ec5989fbe3e2e268cc9831c23596b3b3b385ef29aaeccdcece8ef6ecd94344852f0e1b376ea4a8a8287afefc398d1a358ac2c2c2a8a0a080b66ddb467dfbf6a59f7efa89020303cb9d6f4040807005cb828202ba75eb16ad5dbb96060e1ca8f68d0fda7c019ad930b578cd31e2e26bd70103065083060da86bd7aef4f5d75fd3f9f3e7293b3bbbc463323232a85bb76ec21fada6aff0bc70e1027dfcf1c7141a1aaa71b9972f5fa641830695b864ab4aa5a21d3b7608dfc55b915be7ce9d355eac7ccf9e3db46fdf3ecacbcba3cf3fff9c162f5e4c4aa592929292e8a38f3ea2a14387d2f2e5cb69ead4a9d4b3674faa53a74e89794ba5d2527f87f9f9f974fdfa75dab8716379bf6ef361aaf19a43c4d7ae5da32953a690afaf2f55ab568d7af4e8418b162da2909010adbf92522693d1ecd9b3e9ecd9b36a173bbf75eb168d1c3992b66cd952ea370d6cdcb891060c18a0f1c5a1485252122d59b284ead6ad5b6eb8fefefe74e4c89112d7782eeef2e5cb3463c60ccac8c8a043870e51bf7efd84179ed0d050f2f5f5a5a0a0207afefc391111bd78f18282838369d3a64d3465ca9412df1b6cd18c28de2aed452231776c0505015bb6e865eff4dab56ba15028d0a3470f74ead4a96ad706fecba3478fb070e142d4ac59138b162dd2f8396a4e4e0e264d9a84fcfc7c7cfffdf75a9d2d54740de6b0b030c4c5c5213d3d1d2a950a6e6e6e68d3a60dba77ef8e264d9a6835c6a74f9fe28b2fbec09c3973e0e0e08009132660f6ecd918366c18944a25366cd880f5ebd72328af8bf6c6000006764944415428089f7ffeb9705e322bc6547658694bd43571509051be272ecbcb972fe9b3cf3ea380808032bf6be7c99327d4be7d7b0240aeaeaee4e9e9497dfbf6a5d8d8583d8eb670cb61ecd8b1b46edd3a4a4f4fa777df7d97264d9a247c97705c5c1c0d1f3e9cead7af4f3b76eca0fcfc7cbd8ecfa819d19a57549618715656162d5dba949a376f4e070f1e2c73f3352424845c5d5d356efe4e9a34498fa3fe9f356bd6d0a041832829298956ad5a45dedede6a5fe47deedc39f2f2f2a2d6ad5bd3fdfbf70d3246a362aef1163197887ffcf1c772a7512814e4e1e14173e7ce2d77afebfaf5ebc9d6d69656ac5841cecece25023e79f2a45843afb0f3e7cf938f8f0f85848450484808356ad488366dda24bc1829140a5abc78317df4d147061ba35130f7788b987ac431313104807af5ea45c78f1f273f3f3f5abf7ebdc6cf931f3e7c58e6bc6432198d1e3d9a6c6d6de9f0e1c34444141c1c4cbebebeb462c50a6ad2a409cd9d3b57675ffaa5add8d8586adbb62d7dfdf5d7f4f8f163ead2a50b0d1a3448ed39c7c6c6eae5ab3f8d92a5c45bc494235eb76e9dc6cddca3478f56683e8f1f3fa676edda51b56ad5e8fcf9f31aa731a620b2b3b3e9fdf7dfa7ae5dbbd283070fe8934f3e217777770a0e0e36f4d00ccbd2e22d62aa11af5cb9b244bc5e5e5e153a38e1e2c58b54a74e1d727575a5df7efb4d87a315974aa5a2952b5792878707e5e6e6d2f7df7f4fd5aa55a32fbffcd2327764596abc454c3162a55249ddbb7727a0f0f0c1952b57524c4c8cd68f5fb76e1d49a552f2f0f0a0a8a8281d8e5477ce9d3b27ec07b87dfb36356bd68c3a77eeacf7bde50665e9f1161135e24f3ed14bc4f1f1f154bb766d3a77ee9cd68f91c9643472e4480240dedede949090a0c311ea5e5e5e9ef0efb4b4341a306000d5a85183c2c2c20c382a3de178d59962c4a1a1a15a6f363e7efc98dab66d4b00a86bd7aec2090ce644a552d1ce9d3b85cf8acd16c7ab992946ac8d8b172f52eddab509000d1e3c58ebc3309911e278cb666e11af5dbb9624120901a0f1e3c71bd55e6556411caf76cc21e2e2ef7701d0fcf9f3cb3c0a8b19398eb7624c3de2b0b030727474246b6b6bdab469935e97cd446606f11ae4e24554781653088006559ed9a79f029b37ebf51a5b57ae5c416262a2e55d3ac69c98c9594506bbfa98a947cc4c9899c40b183060802366066046f102060e18e088991e9959bc8011040c70c44c0fcc305ec04802063862a643661a2f604401031c31d301338e1730b280018e9889c8cce30580b2bf9dcb00ac80070002003cabf2ccb66c01a64d2bfc989d59160b881730c235701151d7c453a7029b36f19ad8525848bc8011070c70c4ac122c285ec0c803063862560116162f600201031c31d38205c60b18e14e2c4d44ddb1f5af7ff18e2d73236ebcbfc044e2054c24604007114f9fce119b03f1e3ed6f2af10226b2095d9ca89bd39f7d066cdcc89bd3a6cac2e335597f5d1420419413b13ffbcce097e7619520eec9f861667f250d63c3115b308ed73c70c41688e3352f1cb105e178cd13476c01385ef3c6119b318ed732881af1b4691cb131e0782d0b476c46385ecbc4119b018ed7b271c4268ce36500476c92385e561c476c42385ea609476c02385e561651239e3e9d231613c7cbb4c1111b218e975504476c44385e56191cb111e078595570c406c4f1323170c406c0f1323171c47ac4f1325d1035e2193338624d6432a280008e97e90647ac431c2fd3078e5807385ea64f1cb188385e66081cb108385e66481c711570bccc1870c495c0f13263227ac4e68ce365c68823d602c7cb8c19475c068e9799028e58038e9799128eb8188e9799228e98385e66da2c3a628e97990351239e39d3d0596a87e365e6c4a222e6789939b28888395e66cecc3a628e975902b38c98e36596c4ac22e6789925328b88395e66c94c3a628e97319123fefc738e97317d33a988395ec64a328988395ec64a67d41173bc8c95cf2823e67819d39e5145ccf1325671a2463c6b16c7cb98be1934628e97b1aa3348c41c2f63e2d16bc41c2f63e2d34bc41c2f63baa3d388395ec6744f271173bc8ce98fa8114f9fcef132a66fa246ccf132a67f461431c7cb58651841c41c2f635561c088395ec6c4608088395ec6c4a4c788395ec674410f1173bc8ce9920e23e67819d3071d44ccf132a64f2246ccf13266082244ccf1326648558898e365cc185422628e973163528188395ec68c91161173bc8c19b33222e6781933051a22e678193325c522e678193345047872bc8c31c6186362fb7f01638d6632f395000000000049454e44ae426082', false);
INSERT INTO public.instrument_log_file_attachments VALUES (2, 8, 'ghs02.png', '\x89504e470d0a1a0a0000000d49484452000000f0000000f008060000003e55e9920000000467414d410000b18f0bfc6105000000206348524d00007a26000080840000fa00000080e8000075300000ea6000003a98000017709cba513c00000006624b474400ff00ff00ffa0bda7930000000774494d4507e1080a0328117baaf923000016904944415478daed9d7b5054e51bc79f5d10918b8aa6425cd214c572f01a9a385eb0d4bca4a3399a8991b72cc72c4dcb1a352b75bc9597917e893fcb1a35c9d110349df23286a428c6082992a0721703454904967d7e7f18fc5cf7c239cb61f7bcbbdfcfccf983dd7379dfc3f9ecf39ef73cef7b880000000000808230911f1379e04c00209ebc014cf417139d62222f9c1100c49397ff5d20310082ca0b8901105c5e480c80e0f2426200049717120320b8bc901800c1e585c400082e2f240640707921310082cb0b8901105c5e480c80e0f2426200049717120320b8bc901800c1e585c400082e2f24064070792131007693373292393c5c29898f637a1e006c256f5414734d0d737939f3e0c188c40008276f2d90180041e585c400082e2f240640e5f2bef186657921310082cb0b8901105c5e480c80e0f24262000497171203204bde40d5c90b8901902cef5555cadb3812ff068901e4b595bc901800c1e585c400082e2f2406407079213180bc82cb0b8901e4155c5e480c20afe0f2426200790597171203c82bb8bc8f4a3c64082406905738796bf9e71f480c20af90f2426200790597171203c8fbef327dba98f2426200790597171203c8eb20406200792131240690171203e018f25ebd7a952b2a2a203180bc2246ded9b367f3d9b367118901e4154dde828202767777e7e8e86834a701e415ed9e77cd9a354c443c6dda34dc1303c82b5a8755f7eedd9988b84d9b365c63cf8e33480c20affcceab87557ab8d8e53eb87125f6c615fb102d4ec1437989e80411756cf0cea64f278a8921d2daefd49e3871c2e0ef83070fdaf7047b78102524100d19a2c4de0610d161480c1c2ef2d6326dda348308dca14307d6ebf58ef89c1812435ec74bd2e8d5ab9781c044c48989898e9aec018921afe3c8abd7ebd9cbcbcb48e059b3663972c6162486bc8e911e79f7ee5d237989883d3c3cb8b4b4141203e1e50d62a22c452e9c19335497db9c9f9f6f526022e24d9b36a92b77babc9c79e040a5243ec9449eb8c21179851e989091916156e02e5dbaa8a3330b9118405ed32427279b159888382e2ece1946314162c82be690c093274f5a14383c3cdc5986224262c82bde78de53a74e591458558f94203180bc869c3e7dba5e81c78c19a3de0afcf30f7344042486bcce3993c6993367ea1558a3d1707a7a3a247600b48e2a2f39506eb31c5c5d5deb3f3fccb47efd7af556c2c383283e9e28224289bd21771a91571cce9d3b576f042622767373e39c9c1c75570691d8b92230130511d1494522efcc994245de5a743a9da4f5aaaaaa68ddba75eaae8c8707d1c183448306291589e391ec81c8ab6a12131325456022627777772e2828507fa510891d3b023bca3deff9f3e7e9fcf9f354515161f53e6a6a6a24affbe0c103dab46993faffc1b82746e41521f2ae5cb99289889b376fce73e6cce1bffffe5bf63e8e1d3b263902d71e4b55831c108921afa8cde6df7fffdd402e5f5f5fd98f7b0e1c38204b6022e2152b56c81eb278ead429480c20afe1e09c7223b9fcfcfcb8b8b858f23e626262640bdcba756bbe77ef9eac114f8181817ce7ce1d488c7b60e7bde77d1c4f4f4fa3e7b8858585347ffe7cc9fbb875eb96ece3969494d0b7df7e2b79fdecec6ccacdcda54f3ef904f7c40091f751dcdddd8d22a456abe5b4b43449dbcf9c395376042622eedcb9b3e4e96777eedcc944c44d9a34e1acac2cdc1323023b77e4ade5f6eddb54595969f4b95eafa798981849fbc8cacab2ead8999999f4f3cf3f4b5af7dab56b4444545d5d6ddf5e6c4462445e3561a907d9dfdf5f5284f4f3f3b32a0213114f98304152391f9df5d2cbcbcbfebdd888c490570dac5ab5aa41c300f3f2f2ac969788b869d3a692641c306080c1761b366cc0232634a19db3d9fc28e7cf9fb7f87d424282c5ef9393931b74fccaca4a8a8b8b93d489f528fbf7efb7ffc943731a91d7de74ead4a941b369bcfffefb0d8ac044c453a64ca927d0fdc31a8dc6601b171717be79f326923d80f3ca7bf7ee5dd66ab5f58e20ba7fffbed97d74ebd6adc102fbfafa5a35da69e7ce9dc8d84213daf99acdb5a4a5a5915eafb7b84e5555159d3d7bd6e477797979949e9edee072141515517171b1c5729ac25cb9d09c7632819d7530fec58b1725adf7f88bcb6a3974e8906265b972e58ad9efccfd48a4a4a4a8eb843a89c45ac8ab0efefcf34f49eb1d3f7edce4e7bb77ef56ac2c96b2b9121313cd46666686c4b8e775cef1bc43870e953c93c6e379cbd7af5f37ea586ac8f2fdf7df9b2c63696929bbb8b898dd4e4ece36ee891d28023b6ae4bd7bf7aee475fffaeb2f49eb555555d1e1c3870d3edbb56b97a2d1cfc5c5c5e4e7bffcf28bc5f1c6797979ea8c0e88c488bcd6b07cf972c9ef236adab4a9e4083972e4c8baed743a1db76fdf5eb1e84b449c909060b28c03070eb4b8ddafbffe8af1c490d7719acd5bb66c6122e2b973e75a5cefce9d3bb204d368349c9a9acaccccfbf6ed53545e22e2e4e464a3329e3d7bb6deed0e1e3c88490120afe3dcf3c6c6c6d65ddc4b972e35bbdecd9b37654bd6b76f5f7ef0e081515aa312cbe3e994d5d5d5dcb76fdf7ab753e57b972031e4b596f8f878830b7cefdebd26d72b2929b14ab47efdfa292e6febd6ad0dca565353c351515192b63d7cf8b038bd869018f2d6c7d1a3470d2ef0162d5a707676b6a49938ecb5f4ebd7afae5cb9b9b93c62c408c9dbeedbb7afde73a2d3e920b1a8bdd0cef69cb769d3a6067f979595d11b6fbc619471e5e9e9496ddbb65545993b76ec48172e5ca077de7987ba76ed4a478e1c516cdf376edca0499326a1771a91578ce7bce6e668deb2658bd1bae1e1e1aa88c0969ef3d6b71c3a74c8ecb9d0ebf51c1111c144c4172e5c505f735ad0b7226a6d252f39618695b9e7a91f7cf08151ba626868a82aca2c675ee9c769d6ac99d9ef76ecd85197452667fe2d9b45e28404a2214310891179ff4f7272b2d968d5a74f1f7ef0e041ddba070f1e54cd7db0b58bb9c89a9f9fcf2d5bb6ac5b2f202040f2fc5b88c490d76ea4a4a458bce0a74e9dca7abdbeae23cbd48476222de6a6997df9e59725cb0e8921af6ab874e952bd17fde2c58beb241e3f7ebcb0f29a1b47bc67cf1e93eb4bcd5083c490d76ee4e4e448baf8232323b9b2b2927ffbed3761051e376e9c51fd333232b8458b1656cdfc018921afdd292d2d952c408f1e3d38313191c3c2c214152b3838d82602af5bb7ce283db46bd7ae66d7efd5ab9718c91ece2431e435a4b2b252768eb3d20313366cd8c0bebebe8d2aaf46a3e1ab57af1ac85b5feaa5b7b7b738195bce2031e4358db7b7b75d9bb61b366ce0949414835e60a597b0b0b0bafa16151549ca9b2622835e78480c7955c933cf3c635781d7ac59c3cccc4949498df663523b01c0912347b85dbb7692b72b2c2c142b775a85126b9590979c741a1c29040404a8a21ccf3fff3c1d3a74883c3d3d15dd6f972e5da877efde141919492fbdf412ddbc79d326492348f640e4b5093366ccb06b04deb66d9b41798e1c3952eff4b5729656ad5a593d9d4f41418178ff509545626d43e445e4ad9fa0a020bb1efff14112c3870fa765cb9629b6ffd2d252aba7f3f1f61630c7c111223122af74ec9d22999e9e6e54a69a9a1ac993e835d6d2ac5933b1ffb1a2766c415e79141616da4d12373737b33dbd972f5f66575757bb95ad73e7cee2ff735520b156aebc6836cbc3d7d7d76ecde83e7dfa188d49ae25242484222323ed765e3a77ee2cfe3f5705cd692de495c7d5ab5765f79e3ef7dc737629eba041832c7ebf60c102d2683476295bcf9e3d1de317dace126b21af3cf2f3f369ca9429545d5d2d799bf0f070550adcad5b370a0b0bb34bd9860e1dea38cd2c35776ce19ed790dab7088e1e3d9a2b2a2a246d73e5ca159bdf63babbbb1bbdc1c1145f7cf185cdcbe6e1e1214e1696c81d5b90d7342121214c443c74e8502e2f2f97b58dad9647277fb7446666a6cd051e366c98e3f65ada58622d9acdd6750e11111d3b768c860f1f4e656565f56e3365ca149b9671ecd8b192d60b0e0e267f7f7f55960dcd692b9bd388bc96d9b871a3d150c0fcfc7c8bdbdcb87143d10c284b8b56ab9595e5f4eaabafda2cfa7a7b7bf3ddbb77cd8ede4224961789b588bcf2e9ddbbb7c1dfa9a9a9d4bf7f7fba74e992d96d82828268c48811362b9f9f9f9fe4f5bb77ef6eb3731719196936032b39391991b821911891571ae5e5e526a75ff5f6f6e6d8d858b3db9d3871c226516ec58a15b2ea93909060d7cc3066e68a8a8aba9153b827b6e29e18f2caa3478f1e662fd2d9b3671bbd5fa816a963651bb2a4a4a4c8aa4b7676b64de49d3c79b2d932444747cbfee181c4864d68f77f978663a7e4005b62e9d9eeb66ddb28242484366fde4cf7eedd33f86ef5ead5b28fa595710bf2c4134fc84e92f0f7f797750c39cdf35abcbdbd69fdfaf526bfcbc9c9a1a54b979a9d47db2150ee36526ba9091dcc44798afc52cc98e1d05178d7ae5d92a24ef3e6cdf9f5d75fe7ddbb77734e4e0e339b9e66d5d23270e040eedfbfbfa475870f1f6e557da44ebbe3ededcd2b57ae6cf09c59b5e4e6e6726868281311af5dbbd631a3efd0a14a45dfd352ee8321b104ae5dbb665533d2d3d393fdfdfd656df3d65b6ff1f9f3e7258dbbfde8a38facaa4f9f3e7d249565debc7966a78a250b93d8575555191df3c08103ece7e757b75e4c4c0ce46d88bc90581e7245b476d9ba752b33338f1933469137049a62f8f0e1925a13f9f9f9466f5da47a5e577afdfa7583ceaafdfbf79b7c17d44f3ffd047965ca6bb23dad21fa8b888610517e835becfffd2fd19b6f123df6463e47a07ffffe36394eed6088850b17d6bbee534f3d65d531a40cae5fbb762d3df9e493d4bc797349fbf4f4f4a41f7ffc916edebc495f7ffd35bdf6da6bd4b66d5b1a3f7e3c9d3e7dda68fd366dda38c68571ff3ed1cb2f131d3ba6c4de9288688486e89e35a994ca45e299331d2e126fdebcb9d1a36f93264d0c121c7af5ea65717d53ef1f96c2f4e9d32de6557ff9e59775eb5a7ae7133d96f32c67cc7166662622afcc66b3c5ae314523f1f6ed0e17895f78e185463f46a74e9dc8cdcdadeeef0d1b3658ecad6505a7b769dab429bdfdf6db74f9f2657af7dd77eb3e973a9cf2fefdfba4d3e9243eb8d058d5bbedec91b7debe6d486c9eae5dbb36faac933e3e3e067f0f1e3c98b66fdf6e20f5e3d258c3e3fb1b3972245dba7489b66edd4aeddbb737f8aea0a040f17afafbfb93979717e495d96c96f4700a12db2f0a979494187d1615154567ce9c31f9bcf7c68d1b561da77660bf8b8b0bad5ebd9a121212e8e9a79f36b96e6e6eaee2f50c090981bc56dcf34a7eba0c89ed2370666626e5e5e5197ddeb3674f4a4949a1d8d8587af6d967eb3ecfc8c8b0ea385aad965c5d5de9871f7ea00f3ffcd0e24c1d49494910586d1d56e8d8b28ec2c242abe74596ba3cda81640abd5ecf478f1ee5d1a347f3d8b163adaac7b265cb78efdebdf5aea7d3e9b855ab568ad7313a3a1a1d56369c991212db30bf39303050f2503b6b5f5762eee5dcb61a90919a9a0a796d0924fe3f6bd7aeb5f91b16ec85dc3450298b8f8f0fd788f4ff175d5e486cfbd13ceddab5e3dbb76fdbb59e1919198d3229c198316320afbd80c40fb134bc50a965fefcf976ade3c489131ba55eebd7af87bc90d8be7cf6d967565fc08f26f45b5a5c5d5ded76af78e0c081467b39b8b5d9639017122b464e4e8ec9593aa42cefbdf71ecf9c3953d2bae1e1e1acd7eb6d5ab7d2d252c93f3272977efdfa415e48ac0e468f1e6dd5451c1a1aca353535fcf9e79f4bca1ddeb16387cdeaa4d7eb79f2e4c99222a99b9b9becba6fdcb811f23aacc4b36609257143de44f8c71f7f3033f3b973e778d4a851169f2db769d3c6ec943d4af3e9a79fd65bf6eeddbbf3a2458b643f0f777777e7a2a222c80b89d5814ea7e3c0c040ab045eb06081c1be2e5ebcc873e7cee5808000b383fc1b9bddbb775b943238389877ecd8c1e9e9e9dcbc7973d9759e356b16e485c4ea62cb962d5609dcb2654b2e2b2b33b9cfacac2cdeb3670faf58b182a3a2a278e4c8913c68d020be71e346a3d5e3cc9933eceeee6e7250ffa44993382e2e8e753a1dd7d4d470efdebdad9abb3a232303f2426275f1e0c1030e0a0ab24ae2d5ab57aba61e7abd9eb3b2b2382e2e8e636363393e3e9ed3d2d28c122e626262acaaeb2bafbc027921b13ab1f6a26edbb6add9b716a8918a8a0aab7aa79b356ba6ce4747901712333357575773b76eddac9278e1c285c2081c1d1d6d9389e721af234a6ce367a172494949e1264d9ac8beb85d5d5d392d2d4df5f256575773870e1d64d72f242444f26b59212f24b62bcb972fb72a42f5ecd9537d17f9636cdfbeddaaf702abeec709f2426273545555f1902143ac9278ce9c39aaad575e5e1efbf8f8c8aed377df7d077921b1581297959571cf9e3dad92f8abafbe5265d3f9c5175f945d97254b96405e482ca6c4454545dca54b17d917bd8b8b8bd513b537d6a3a5a8a828d9f558b46811e485c4624b7cfbf66d1e356a9455f342efdab54b157558bc78b1ec9146d6beea05f24262d5515353c39f7cf289eca47fad56cb6bd7aeb5f928a447cb3d6fde3c5965f6f2f29234c716e485c4c2f54e676666f2b871e36447e3091326489ebb4ac9648d091326c8ee45476f332476688999994f9f3ecd53a74e3599736c6e090808e0f8f8789b94afa4a484070c1820b96c2d5ab4e0cd9b37b34ea783bc90d83924667e38607eebd6ad3c6ad428f6f4f49424cbb061c3382929a9511351a4266ab46cd992972c59a2cea181901712db92caca4a3e71e204af5ab58a274e9cc8c1c1c11627921b3162049f3c7952d1fbe39898987a5b051a8d86c3c2c278e3c68deacddf760279356a9598884e10917f8377366b16d1d75f136934c2fea895979753565616656767d72db9b9b9545c5c4c05050574ebd62df2f5f5a52953a6d0c4891329343494b45aadece3545454d0dcb973e99b6fbe31f9bd9f9f1f858585d1e0c18369fcf8f1141414a4de9326da1b131c4960482c9fb2b2322a2c2ca4e2e262aaacaca4e0e0606ad7ae1d356bd64cd2f6555555f4f1c71f536a6a2af9f8f8909b9b1b05060652606020050505516868a8ba85754279552d30240690577081213180bc96d1aafd7fa2e85b11636288e6cc79d8250120afe0f20a11811b2512cf9e4df49fff2012435ea1e5154a60480c20afe002436200790517581489cbcacae8dcb97390cc041d3a74a08e1d3b425e6746d18cadd9b315cfd84a4a4a6af4b7158aba2c5dba1419560aa115b5e08af64e6fdb86de695bfef836e43c23f23a86c09018f7bc68360b2e302476a2080c791d536048ec0402435ec716f811892388a8401189e7cf87c46a10f8fe7da231639492f73439586fb3d6912e0c0d5126110d5624126fd98248ac967bdee3c7958abc2fe1519108bff02a7fc404f0a8084062c80b7921b1e4e5cd372131e4059018405e0089212fe485c49018f202480c202fb0a9c4f98a5c30efbc03891b2a6f448452f226425e44624462445e008901e4059018f2425e0089212f80c49018f202480c79212f80c4901780469778fe7ce79618f202480c79212fb0afc4efbeeb5c12435e0089212fe4059018f202480c89212f80c48e2a31e4059018f2425e209ec49017f202480c790180c490174062879618f202482ca8c490174062412586bc00120b2a31e40590585089212f80c4824a0c790124165462c80b20b1a012435e00049518f20220a8c4901700412586bc00082a31e405c0c612bff71ee405c0a92586bc00082a31e405405089212f00824a0c7901105462c80b80a012435e00049518f20220a8c49017009b4b9caf58c656448452f226425e006c1d89117901706a89212f00824a0c7901105462c80b80a012435e00049518f20220a8c4901700412586bc00082a31e405405089212f00824a0c7901105462c80b80a012435e00049518f20220a8c4901700412586bc00082a31e405405089212f00824afc34e40500000000509aff01068bb5dce04e89130000002574455874646174653a63726561746500323031372d30382d31305430333a34303a31362b30303a303033ce9da10000002574455874646174653a6d6f6469667900323031372d30382d31305430333a34303a31362b30303a30304293251d0000000049454e44ae426082', false);
INSERT INTO public.instrument_log_file_attachments VALUES (3, 8, 'test.txt', '\x5468697320697320612074657374', false);


--
-- Data for Name: instrument_log_object_attachments; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.instrument_log_object_attachments VALUES (1, 8, 10, false);
INSERT INTO public.instrument_log_object_attachments VALUES (2, 8, 9, false);
INSERT INTO public.instrument_log_object_attachments VALUES (3, 8, 8, false);
INSERT INTO public.instrument_log_object_attachments VALUES (4, 8, 7, false);
INSERT INTO public.instrument_log_object_attachments VALUES (5, 8, 6, false);
INSERT INTO public.instrument_log_object_attachments VALUES (6, 8, 5, false);
INSERT INTO public.instrument_log_object_attachments VALUES (7, 8, 4, false);
INSERT INTO public.instrument_log_object_attachments VALUES (8, 8, 3, false);
INSERT INTO public.instrument_log_object_attachments VALUES (9, 8, 2, false);
INSERT INTO public.instrument_log_object_attachments VALUES (10, 8, 1, false);


--
-- Data for Name: instrument_translations; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.instrument_translations VALUES (1, 1, -99, 'OMBE I', 'This is an example instrument', '# Header
This example shows how Markdown can be used for instrument Notes.

## Subheader

*italics* **bold**


| A | B | C |
|--:|:-:|---|
| Example | 100˚C | 5µm |
| Data | 110˚C | 6µm |
            ', 'This is the short description');
INSERT INTO public.instrument_translations VALUES (2, 1, -98, 'OMBE I', 'Dies ist ein Beispiel Instrument', '# Header
This example shows how Markdown can be used for instrument Notes.

## Subheader

*italics* **bold**


| A | B | C |
|--:|:-:|---|
| Example | 100˚C | 5µm |
| Data | 110˚C | 6µm |
            ', 'Dies ist die kurze Beschreibung');
INSERT INTO public.instrument_translations VALUES (3, 2, -99, 'XRR', 'X-Ray Reflectometry', '', '');
INSERT INTO public.instrument_translations VALUES (4, 3, -99, 'MPMS SQUID', 'MPMS SQUID Magnetometer JCNS-2', '', '');
INSERT INTO public.instrument_translations VALUES (5, 4, -99, 'Powder Diffractometer', 'Huber Imaging Plate Guinier Camera G670 at JCNS-2', '', '');
INSERT INTO public.instrument_translations VALUES (6, 5, -99, 'GALAXI', 'Gallium Anode Low-Angle X-ray Instrument', '', '');


--
-- Data for Name: instruments; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.instruments VALUES (1, true, false, false, false, true, false, false, '');
INSERT INTO public.instruments VALUES (2, false, false, false, false, false, false, false, '');
INSERT INTO public.instruments VALUES (3, false, false, false, false, false, false, false, '');
INSERT INTO public.instruments VALUES (4, false, false, false, false, false, false, false, '');
INSERT INTO public.instruments VALUES (5, false, false, false, false, false, false, false, '');


--
-- Data for Name: languages; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.languages VALUES (-99, 'en', '{"en": "English", "de": "Englisch"}', '%Y-%m-%d %H:%M:%S', 'YYYY-MM-DD HH:mm:ss', true, true);
INSERT INTO public.languages VALUES (-98, 'de', '{"en": "German", "de": "Deutsch"}', '%d.%m.%Y %H:%M:%S', 'DD.MM.YYYY HH:mm:ss', true, true);


--
-- Data for Name: locations; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.locations VALUES (1, '{"en": "Campus"}', '{"en": "Max Mustermann Campus"}', NULL);
INSERT INTO public.locations VALUES (2, '{"en": "Building A", "de": "Geb\u00e4ude A"}', '{"en": "Building A on Max Mustermann Campus", "de": "Geb\u00e4ude A auf dem Max Mustermann Campus"}', 1);
INSERT INTO public.locations VALUES (3, '{"en": "Room 42a", "de": "Raum 42a"}', '{"en": "Building A, Room 42a", "de": "Geb\u00e4ude A, Raum 42a"}', 2);
INSERT INTO public.locations VALUES (4, '{"en": "Room 42b", "de": "Raum 42b"}', '{"en": "Building A, Room 42b", "de": "Geb\u00e4ude A, Raum 42b"}', 2);


--
-- Data for Name: markdown_images; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: markdown_to_html_cache_entries; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: migration_index; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.migration_index VALUES (66);


--
-- Data for Name: notification_mode_for_types; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.notifications VALUES (1, 'INSTRUMENT_LOG_ENTRY_CREATED', 2, '{"instrument_log_entry_id": 1}', false, '2021-07-02 08:29:27.949743');
INSERT INTO public.notifications VALUES (2, 'INSTRUMENT_LOG_ENTRY_CREATED', 2, '{"instrument_log_entry_id": 2}', false, '2021-07-02 08:29:27.974425');
INSERT INTO public.notifications VALUES (3, 'INSTRUMENT_LOG_ENTRY_CREATED', 2, '{"instrument_log_entry_id": 3}', false, '2021-07-02 08:29:27.995997');
INSERT INTO public.notifications VALUES (4, 'INSTRUMENT_LOG_ENTRY_CREATED', 2, '{"instrument_log_entry_id": 4}', false, '2021-07-02 08:29:28.017453');
INSERT INTO public.notifications VALUES (5, 'INSTRUMENT_LOG_ENTRY_CREATED', 2, '{"instrument_log_entry_id": 5}', false, '2021-07-02 08:29:28.038077');
INSERT INTO public.notifications VALUES (6, 'INSTRUMENT_LOG_ENTRY_CREATED', 2, '{"instrument_log_entry_id": 6}', false, '2021-07-02 08:29:28.0565');
INSERT INTO public.notifications VALUES (7, 'INSTRUMENT_LOG_ENTRY_CREATED', 2, '{"instrument_log_entry_id": 7}', false, '2021-07-02 08:29:28.077158');
INSERT INTO public.notifications VALUES (8, 'INSTRUMENT_LOG_ENTRY_CREATED', 2, '{"instrument_log_entry_id": 8}', false, '2021-07-02 08:29:28.104743');
INSERT INTO public.notifications VALUES (9, 'ASSIGNED_AS_RESPONSIBLE_USER', 2, '{"object_id": 8, "assigner_id": 3, "object_location_assignment_id": 2, "confirmation_url": "http://localhost:5000/locations/confirm_responsibility?t=Mg.YN7OaQ.e2K8UML6xMoOGSJGXkpPPlOor-U"}', false, '2021-07-02 08:29:29.378029');
INSERT INTO public.notifications VALUES (10, 'OTHER', 2, '{"message": "This is a demo."}', false, '2021-07-02 08:29:29.387122');
INSERT INTO public.notifications VALUES (11, 'RECEIVED_OBJECT_PERMISSIONS_REQUEST', 2, '{"object_id": 4, "requester_id": 1}', false, '2021-07-02 08:29:29.396282');


--
-- Data for Name: object_location_assignments; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.object_location_assignments VALUES (1, 8, 3, NULL, 2, '{"en": "Temporarily stored on table\n\nSome other text", "de": "Tempor\u00e4r auf einem Tisch gelagert \n\n Irgendein anderer Text"}', '2021-07-02 08:29:29.352839', false);
INSERT INTO public.object_location_assignments VALUES (2, 8, 4, 2, 3, '{"en": "Stored in shelf K", "de": "In Regal K gelagert"}', '2021-07-02 08:29:29.368782', false);


--
-- Data for Name: object_log_entries; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.object_log_entries VALUES (1, 'CREATE_OBJECT', 1, 2, '{}', '2021-07-02 08:29:28.349759');
INSERT INTO public.object_log_entries VALUES (2, 'CREATE_OBJECT', 2, 2, '{}', '2021-07-02 08:29:28.415282');
INSERT INTO public.object_log_entries VALUES (3, 'POST_COMMENT', 1, 2, '{"comment_id": 1}', '2021-07-02 08:29:28.426416');
INSERT INTO public.object_log_entries VALUES (4, 'POST_COMMENT', 1, 2, '{"comment_id": 2}', '2021-07-02 08:29:28.43587');
INSERT INTO public.object_log_entries VALUES (5, 'UPLOAD_FILE', 1, 2, '{"file_id": 0}', '2021-07-02 08:29:28.452893');
INSERT INTO public.object_log_entries VALUES (6, 'UPLOAD_FILE', 1, 2, '{"file_id": 1}', '2021-07-02 08:29:28.463966');
INSERT INTO public.object_log_entries VALUES (7, 'UPLOAD_FILE', 1, 2, '{"file_id": 2}', '2021-07-02 08:29:28.489028');
INSERT INTO public.object_log_entries VALUES (8, 'LINK_PROJECT', 1, 2, '{"project_id": 1}', '2021-07-02 08:29:28.499757');
INSERT INTO public.object_log_entries VALUES (9, 'CREATE_OBJECT', 3, 2, '{}', '2021-07-02 08:29:28.647326');
INSERT INTO public.object_log_entries VALUES (10, 'CREATE_OBJECT', 4, 2, '{}', '2021-07-02 08:29:28.673056');
INSERT INTO public.object_log_entries VALUES (11, 'CREATE_OBJECT', 5, 3, '{}', '2021-07-02 08:29:28.881448');
INSERT INTO public.object_log_entries VALUES (12, 'CREATE_OBJECT', 6, 3, '{}', '2021-07-02 08:29:28.919764');
INSERT INTO public.object_log_entries VALUES (13, 'USE_OBJECT_IN_SAMPLE_CREATION', 5, 3, '{"sample_id": 6}', '2021-07-02 08:29:28.925394');
INSERT INTO public.object_log_entries VALUES (14, 'EDIT_OBJECT', 5, 3, '{"version_id": 1}', '2021-07-02 08:29:28.957024');
INSERT INTO public.object_log_entries VALUES (15, 'USE_OBJECT_IN_SAMPLE_CREATION', 6, 3, '{"sample_id": 5}', '2021-07-02 08:29:28.96193');
INSERT INTO public.object_log_entries VALUES (16, 'CREATE_OBJECT', 7, 3, '{}', '2021-07-02 08:29:28.984298');
INSERT INTO public.object_log_entries VALUES (17, 'USE_OBJECT_IN_MEASUREMENT', 5, 3, '{"measurement_id": 7}', '2021-07-02 08:29:28.988246');
INSERT INTO public.object_log_entries VALUES (18, 'CREATE_OBJECT', 8, 2, '{}', '2021-07-02 08:29:29.016617');
INSERT INTO public.object_log_entries VALUES (19, 'USE_OBJECT_IN_MEASUREMENT', 6, 2, '{"measurement_id": 8}', '2021-07-02 08:29:29.020391');
INSERT INTO public.object_log_entries VALUES (20, 'CREATE_OBJECT', 9, 3, '{}', '2021-07-02 08:29:29.214387');
INSERT INTO public.object_log_entries VALUES (21, 'CREATE_OBJECT', 10, 3, '{}', '2021-07-02 08:29:29.306044');
INSERT INTO public.object_log_entries VALUES (22, 'ASSIGN_LOCATION', 8, 2, '{"object_location_assignment_id": 1}', '2021-07-02 08:29:29.358864');
INSERT INTO public.object_log_entries VALUES (23, 'ASSIGN_LOCATION', 8, 3, '{"object_location_assignment_id": 2}', '2021-07-02 08:29:29.380755');


--
-- Data for Name: object_publications; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: objects_current; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.objects_current VALUES (1, 0, 1, '{"name": {"text": {"en": "OMBE-1"}, "_type": "text"}, "created": {"_type": "datetime", "utc_datetime": "2017-02-24 11:56:00"}, "checkbox": {"_type": "bool", "value": false}, "dropdown": {"text": "Option B", "_type": "text"}, "substrate": {"text": {"en": "GaAs"}, "_type": "text"}, "multilayer": [{"films": [{"name": {"text": {"en": "Seed Layer"}, "_type": "text"}, "elements": [{"name": {"text": "Fe", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 0.09999999999999999, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.00000000001}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 5.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.0000000005}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 130.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 403.15}}], "repetitions": {"_type": "quantity", "units": "1", "magnitude": 1.0, "dimensionality": "dimensionless", "magnitude_in_base_units": 1}}, {"films": [{"name": {"text": {"en": "Buffer Layer"}, "_type": "text"}, "elements": [{"name": {"text": "Ag", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 1.0, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.0000000001}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 1500.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.00000015}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 130.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 403.15}}], "repetitions": {"_type": "quantity", "units": "1", "magnitude": 1.0, "dimensionality": "dimensionless", "magnitude_in_base_units": 1}}, {"films": [{"name": {"text": {"en": "Pd"}, "_type": "text"}, "elements": [{"name": {"text": "Pd", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 0.01, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.000000000001}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 150.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.000000015}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 100.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 373.15}}, {"name": {"text": {"en": "Fe"}, "_type": "text"}, "elements": [{"name": {"text": "Fe", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 0.049999999999999996, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.000000000005}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 10.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.000000001}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 130.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 403.15}}], "repetitions": {"_type": "quantity", "units": "1", "magnitude": 10.0, "dimensionality": "dimensionless", "magnitude_in_base_units": 10}}, {"films": [{"name": {"text": {"en": "Pd Layer"}, "_type": "text"}, "elements": [{"name": {"text": "Pd", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 0.09999999999999999, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.00000000001}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 150.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.000000015}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 100.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 373.15}}], "repetitions": {"_type": "quantity", "units": "1", "magnitude": 1.0, "dimensionality": "dimensionless", "magnitude_in_base_units": 1}}]}', '{"type": "object", "title": "Sample Information", "required": ["name", "created", "checkbox", "substrate", "dropdown", "multilayer"], "properties": {"name": {"type": "text", "title": {"en": "Sample Name"}, "default": "OMBE-", "pattern": "^OMBE-[0-9]+$", "maxLength": 100, "minLength": 1}, "created": {"type": "datetime", "title": {"en": "Creation Datetime"}}, "checkbox": {"type": "bool", "title": {"en": "Checkbox"}}, "dropdown": {"type": "text", "title": {"en": "Dropdown"}, "choices": ["Option A", "Option B", "Option C"]}, "substrate": {"type": "text", "title": {"en": "Substrate"}, "minLength": 1, "dataverse_export": true}, "multilayer": {"type": "array", "items": {"type": "object", "title": "Multilayer", "properties": {"films": {"type": "array", "items": {"type": "object", "title": "Film", "properties": {"name": {"type": "text", "title": "Film Name", "minLength": 1}, "elements": {"type": "array", "items": {"type": "object", "title": "Element", "properties": {"name": {"type": "text", "title": "Element Name", "minLength": 1}, "rate": {"type": "quantity", "title": "Rate", "units": "Å / s"}, "fraction": {"type": "quantity", "title": "Fraction", "units": "1"}, "frequency_change": {"type": "quantity", "title": "Frequency Change", "units": "Hz / s"}}, "propertyOrder": ["name", "frequency_change", "fraction", "rate"]}, "style": "table", "title": "Elements", "minItems": 1}, "thickness": {"type": "quantity", "title": "Film Thickness", "units": "Å"}, "oxygen_flow": {"type": "quantity", "title": "Oxygen Flow", "units": "sccm"}, "substrate_temperature": {"type": "quantity", "title": "Substrate Temperature", "units": "degC"}}, "propertyOrder": ["name", "thickness", "oxygen_flow", "substrate_temperature", "elements"]}, "title": "Films", "minItems": 1}, "repetitions": {"type": "quantity", "title": "Film Layer Repetitions", "units": "1", "default": 1}}, "propertyOrder": ["repetitions", "films"]}, "title": {"en": "Multilayers"}, "minItems": 1}}, "propertyOrder": ["name", "created", "checkbox", "dropdown", "substrate", "multilayer"], "displayProperties": ["substrate"]}', 2, '2021-07-02 08:29:28.286865');
INSERT INTO public.objects_current VALUES (2, 0, 2, '{"name": {"text": {"en": "OMBE-1"}, "_type": "text"}, "created": {"_type": "datetime", "utc_datetime": "2017-02-24 11:56:00"}, "checkbox": {"_type": "bool", "value": false}, "dropdown": {"text": "Option B", "_type": "text"}, "substrate": {"text": {"en": "GaAs"}, "_type": "text"}, "multilayer": [{"films": [{"name": {"text": {"en": "Seed Layer"}, "_type": "text"}, "elements": [{"name": {"text": "Fe", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 0.09999999999999999, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.00000000001}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 5.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.0000000005}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 130.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 403.15}}], "repetitions": {"_type": "quantity", "units": "1", "magnitude": 1.0, "dimensionality": "dimensionless", "magnitude_in_base_units": 1}}, {"films": [{"name": {"text": {"en": "Buffer Layer"}, "_type": "text"}, "elements": [{"name": {"text": "Ag", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 1.0, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.0000000001}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 1500.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.00000015}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 130.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 403.15}}], "repetitions": {"_type": "quantity", "units": "1", "magnitude": 1.0, "dimensionality": "dimensionless", "magnitude_in_base_units": 1}}, {"films": [{"name": {"text": {"en": "Pd"}, "_type": "text"}, "elements": [{"name": {"text": "Pd", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 0.01, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.000000000001}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 150.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.000000015}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 100.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 373.15}}, {"name": {"text": {"en": "Fe"}, "_type": "text"}, "elements": [{"name": {"text": "Fe", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 0.049999999999999996, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.000000000005}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 10.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.000000001}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 130.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 403.15}}], "repetitions": {"_type": "quantity", "units": "1", "magnitude": 10.0, "dimensionality": "dimensionless", "magnitude_in_base_units": 10}}, {"films": [{"name": {"text": {"en": "Pd Layer"}, "_type": "text"}, "elements": [{"name": {"text": "Pd", "_type": "text"}, "rate": {"_type": "quantity", "units": "Å/s", "magnitude": 0.09999999999999999, "dimensionality": "[length] / [time]", "magnitude_in_base_units": 0.00000000001}}], "thickness": {"_type": "quantity", "units": "Å", "magnitude": 150.0, "dimensionality": "[length]", "magnitude_in_base_units": 0.000000015}, "oxygen_flow": {"_type": "quantity", "units": "sccm", "magnitude": 0.0, "dimensionality": "[length] ** 3 / [time]", "magnitude_in_base_units": 0}, "substrate_temperature": {"_type": "quantity", "units": "degC", "magnitude": 100.0, "dimensionality": "[temperature]", "magnitude_in_base_units": 373.15}}], "repetitions": {"_type": "quantity", "units": "1", "magnitude": 1.0, "dimensionality": "dimensionless", "magnitude_in_base_units": 1}}]}', '{"type": "object", "title": "Sample Information", "required": ["name", "created", "checkbox", "substrate", "dropdown", "multilayer"], "properties": {"name": {"type": "text", "title": {"en": "Sample Name"}, "default": "OMBE-", "pattern": "^OMBE-[0-9]+$", "maxLength": 100, "minLength": 1}, "created": {"type": "datetime", "title": {"en": "Creation Datetime"}}, "checkbox": {"type": "bool", "title": {"en": "Checkbox"}}, "dropdown": {"type": "text", "title": {"en": "Dropdown"}, "choices": ["Option A", "Option B", "Option C"]}, "substrate": {"type": "text", "title": {"en": "Substrate"}, "minLength": 1, "dataverse_export": true}, "multilayer": {"type": "array", "items": {"type": "object", "title": "Multilayer", "properties": {"films": {"type": "array", "items": {"type": "object", "title": "Film", "properties": {"name": {"type": "text", "title": "Film Name", "minLength": 1}, "elements": {"type": "array", "items": {"type": "object", "title": "Element", "properties": {"name": {"type": "text", "title": "Element Name", "minLength": 1}, "rate": {"type": "quantity", "title": "Rate", "units": "Å / s"}, "fraction": {"type": "quantity", "title": "Fraction", "units": "1"}, "frequency_change": {"type": "quantity", "title": "Frequency Change", "units": "Hz / s"}}, "propertyOrder": ["name", "frequency_change", "fraction", "rate"]}, "style": "table", "title": "Elements", "minItems": 1}, "thickness": {"type": "quantity", "title": "Film Thickness", "units": "Å"}, "oxygen_flow": {"type": "quantity", "title": "Oxygen Flow", "units": "sccm"}, "substrate_temperature": {"type": "quantity", "title": "Substrate Temperature", "units": "degC"}}, "propertyOrder": ["name", "thickness", "oxygen_flow", "substrate_temperature", "elements"]}, "title": "Films", "minItems": 1}, "repetitions": {"type": "quantity", "title": "Film Layer Repetitions", "units": "1", "default": 1}}, "propertyOrder": ["repetitions", "films"]}, "title": {"en": "Multilayers"}, "minItems": 1}}, "propertyOrder": ["name", "created", "checkbox", "dropdown", "substrate", "multilayer"], "displayProperties": ["substrate"]}', 2, '2021-07-02 08:29:28.355361');
INSERT INTO public.objects_current VALUES (3, 0, 5, '{"mass": {"_type": "quantity", "units": "mg", "magnitude": 10.0, "dimensionality": "[mass]", "magnitude_in_base_units": 0.00001}, "name": {"text": {"de": "TEST-1", "en": "TEST-1"}, "_type": "text"}, "tags": {"tags": ["tag1", "tag2"], "_type": "tags"}}', '{"type": "object", "title": "Minimal Object", "required": ["name"], "properties": {"mass": {"type": "quantity", "title": "Mass", "units": "kg"}, "name": {"type": "text", "title": "Object Name", "languages": "all"}, "tags": {"type": "tags", "title": "Tags"}}, "propertyOrder": ["name", "tags", "mass"], "displayProperties": ["tags", "mass"]}', 2, '2021-07-02 08:29:28.636136');
INSERT INTO public.objects_current VALUES (4, 0, 5, '{"mass": {"_type": "quantity", "units": "mg", "magnitude": 5.0, "dimensionality": "[mass]", "magnitude_in_base_units": 0.000005}, "name": {"text": {"en": "TEST-2"}, "_type": "text"}, "tags": {"tags": ["tag2", "tag3"], "_type": "tags"}}', '{"type": "object", "title": "Minimal Object", "required": ["name"], "properties": {"mass": {"type": "quantity", "title": "Mass", "units": "kg"}, "name": {"type": "text", "title": "Object Name", "languages": "all"}, "tags": {"type": "tags", "title": "Tags"}}, "propertyOrder": ["name", "tags", "mass"], "displayProperties": ["tags", "mass"]}', 2, '2021-07-02 08:29:28.662706');
INSERT INTO public.objects_current VALUES (6, 0, 10, '{"name": {"text": {"de": "Objekt 2", "en": "Object 2"}, "_type": "text"}, "sample": {"_type": "sample", "object_id": 5}}', '{"type": "object", "title": "Example Object", "required": ["name"], "properties": {"name": {"type": "text", "title": {"de": "Objektname", "en": "Object Name"}, "languages": "all"}, "sample": {"type": "sample", "title": {"de": "Probe", "en": "Sample"}}}}', 3, '2021-07-02 08:29:28.903413');
INSERT INTO public.objects_current VALUES (5, 1, 10, '{"name": {"text": {"de": "Objekt 1", "en": "Object 1"}, "_type": "text"}, "sample": {"_type": "sample", "object_id": 6}}', '{"type": "object", "title": "Example Object", "required": ["name"], "properties": {"name": {"type": "text", "title": {"de": "Objektname", "en": "Object Name"}, "languages": "all"}, "sample": {"type": "sample", "title": {"de": "Probe", "en": "Sample"}}}}', 3, '2021-07-02 08:29:28.93912');
INSERT INTO public.objects_current VALUES (7, 0, 11, '{"name": {"text": {"de": "Messung", "en": "Measurement"}, "_type": "text"}, "sample": {"_type": "sample", "object_id": 5}, "comment": {"text": {"en": "This is a test.\nThis **is** a *second* line.\n\nThis line follows an empty line."}, "_type": "text", "is_markdown": true}}', '{"type": "object", "title": "Example Object", "required": ["name"], "properties": {"name": {"type": "text", "title": "Object Name", "languages": ["en", "de"]}, "sample": {"type": "sample", "title": "Sample"}, "comment": {"type": "text", "title": {"de": "Kommentar", "en": "Comment"}, "markdown": true, "languages": "all"}}}', 3, '2021-07-02 08:29:28.967658');
INSERT INTO public.objects_current VALUES (8, 0, 11, '{"name": {"text": {"de": "Messung 2", "en": "Measurement 2"}, "_type": "text"}, "sample": {"_type": "sample", "object_id": 6}, "comment": {"text": {"en": "This is a test.\nThis is a second line.\n\nThis line follows an empty line."}, "_type": "text"}}', '{"type": "object", "title": "Example Object", "required": ["name"], "properties": {"name": {"type": "text", "title": "Object Name", "languages": ["en", "de"]}, "sample": {"type": "sample", "title": "Sample"}, "comment": {"type": "text", "title": {"de": "Kommentar", "en": "Comment"}, "markdown": true, "languages": "all"}}}', 2, '2021-07-02 08:29:29.000699');
INSERT INTO public.objects_current VALUES (9, 0, 12, '{"name": {"text": "Plotly Example Data #1", "_type": "text"}, "plot1": {"_type": "plotly_chart", "plotly": {"data": [{"x": ["0.000", "0.100", "0.200", "0.300", "0.400", "0.500", "0.550", "0.600", "0.700", "0.800", "0.900", "1.000", "1.100", "1.200", "1.300", "1.400", "1.500", "1.600", "1.700", "1.800", "1.900", "2.000", "2.100", "2.200", "2.300", "2.400", "2.500", "2.600", "2.700", "2.800", "2.900", "3.000", "3.100", "3.200", "3.300", "3.400", "3.500", "3.600", "3.700", "3.800", "3.900", "4.000", "4.100", "4.200", "4.300", "4.400", "4.500", "4.600", "4.700", "4.800", "4.900", "5.000", "5.100", "5.200", "5.300", "5.400", "5.500", "5.600", "5.700", "5.800", "5.900", "6.000", "6.100", "6.200", "6.300", "6.400", "6.500", "6.600", "6.700", "6.800", "6.900", "7.000", "7.100", "7.200", "7.300", "7.400", "7.500", "7.600", "7.700", "7.800", "7.900", "8.000", "8.100", "8.200", "8.300", "8.400", "8.500", "8.600", "8.700", "8.800", "8.900", "9.000", "9.100", "9.200", "9.300", "9.400", "9.500", "9.600", "9.700", "9.800", "9.900", "10.000", "10.100", "10.200", "10.300", "10.400", "10.500", "10.600", "10.700", "10.800", "10.900", "11.000", "11.100", "11.200", "11.300", "11.400", "11.500", "11.600", "11.700", "11.800", "11.900", "12.000", "12.100", "12.200", "12.300", "12.400", "12.500", "12.600", "12.700", "12.800", "12.900", "13.000", "13.100", "13.200", "13.300", "13.400", "13.500", "13.600", "13.700", "13.800", "13.900", "14.000", "14.100", "14.200", "14.300", "14.400", "14.500", "14.600", "14.700", "14.800", "14.900", "15.000", "15.100", "15.200", "15.300", "15.400", "15.500", "15.600", "15.700", "15.800", "15.900", "16.000", "16.100", "16.200", "16.300", "16.400", "16.500", "16.600", "16.700", "16.800", "16.900", "17.000", "17.100", "17.200", "17.300", "17.400", "17.500", "17.600", "17.700", "17.800", "17.900"], "y": ["0.000", "0.153", "0.297", "0.428", "0.543", "0.640", "0.718", "0.775", "0.810", "0.825", "0.819", "0.793", "0.748", "0.687", "0.611", "0.524", "0.427", "0.323", "0.216", "0.107", "0.000", "-0.103", "-0.199", "-0.287", "-0.364", "-0.429", "-0.481", "-0.519", "-0.543", "-0.553", "-0.549", "-0.531", "-0.501", "-0.461", "-0.410", "-0.351", "-0.286", "-0.217", "-0.145", "-0.072", "0.000", "0.069", "0.133", "0.192", "0.244", "0.287", "0.322", "0.348", "0.364", "0.371", "0.368", "0.356", "0.336", "0.309", "0.275", "0.235", "0.192", "0.145", "0.097", "0.048", "0.000", "-0.046", "-0.089", "-0.129", "-0.163", "-0.193", "-0.216", "-0.233", "-0.244", "-0.248", "-0.247", "-0.239", "-0.225", "-0.207", "-0.184", "-0.158", "-0.129", "-0.097", "-0.065", "-0.032", "0.000", "0.031", "0.060", "0.086", "0.110", "0.129", "0.145", "0.156", "0.164", "0.167", "0.165", "0.160", "0.151", "0.139", "0.123", "0.106", "0.086", "0.065", "0.044", "0.022", "0.000", "-0.021", "-0.040", "-0.058", "-0.073", "-0.087", "-0.097", "-0.105", "-0.110", "-0.112", "-0.111", "-0.107", "-0.101", "-0.093", "-0.083", "-0.071", "-0.058", "-0.044", "-0.029", "-0.014", "0.000", "0.014", "0.027", "0.039", "0.049", "0.058", "0.065", "0.070", "0.074", "0.075", "0.074", "0.072", "0.068", "0.062", "0.055", "0.048", "0.039", "0.029", "0.020", "0.010", "0.000", "-0.009", "-0.018", "-0.026", "-0.033", "-0.039", "-0.044", "-0.047", "-0.049", "-0.050", "-0.050", "-0.048", "-0.045", "-0.042", "-0.037", "-0.032", "-0.026", "-0.020", "-0.013", "-0.007", "0.000", "0.006", "0.012", "0.017", "0.022", "0.026", "0.029", "0.032", "0.033", "0.034", "0.033", "0.032", "0.030", "0.028", "0.025", "0.021", "0.017", "0.013", "0.009", "0.004"], "name": "Emerald Blue", "type": "bar", "marker": {"color": "rgb(0, 0, 238)"}}, {"x": ["0.000", "0.100", "0.200", "0.300", "0.400", "0.500", "0.600", "0.700", "0.800", "0.900", "1.000", "1.100", "1.200", "1.300", "1.400", "1.500", "1.600", "1.700", "1.800", "1.900", "2.000", "2.100", "2.200", "2.300", "2.400", "2.500", "2.600", "2.700", "2.800", "2.900", "3.000", "3.100", "3.200", "3.300", "3.400", "3.500", "3.600", "3.700", "3.800", "3.900", "4.000", "4.100", "4.200", "4.300", "4.400", "4.500", "4.600", "4.700", "4.800", "4.900", "5.000", "5.100", "5.200", "5.300", "5.400", "5.500", "5.600", "5.700", "5.800", "5.900", "6.000", "6.100", "6.200", "6.300", "6.400", "6.500", "6.600", "6.700", "6.800", "6.900", "7.000", "7.100", "7.200", "7.300", "7.400", "7.500", "7.600", "7.700", "7.800", "7.900", "8.000", "8.100", "8.200", "8.300", "8.400", "8.500", "8.600", "8.700", "8.800", "8.900", "9.000", "9.100", "9.200", "9.300", "9.400", "9.500", "9.600", "9.700", "9.800", "9.900", "10.000", "10.100", "10.200", "10.300", "10.400", "10.500", "10.600", "10.700", "10.800", "10.900", "11.000", "11.100", "11.200", "11.300", "11.400", "11.500", "11.600", "11.700", "11.800", "11.900", "12.000", "12.100", "12.200", "12.300", "12.400", "12.500", "12.600", "12.700", "12.800", "12.900", "13.000", "13.100", "13.200", "13.300", "13.400", "13.500", "13.600", "13.700", "13.800", "13.900", "14.000", "14.100", "14.200", "14.300", "14.400", "14.500", "14.600", "14.700", "14.800", "14.900", "15.000", "15.100", "15.200", "15.300", "15.400", "15.500", "15.600", "15.700", "15.800", "15.900", "16.000", "16.100", "16.200", "16.300", "16.400", "16.500", "16.600", "16.700", "16.800", "16.900", "17.000", "17.100", "17.200", "17.300", "17.400", "17.500", "17.600", "17.700", "17.800", "17.900"], "y": ["0.866888888888888888888888888888888888888888888888888888888888888888888888888888", "0.915", "0.940", "0.940", "0.918", "0.874", "0.810", "0.729", "0.633", "0.526", "0.409", "0.288", "0.164", "0.040", "-0.079", "-0.192", "-0.295", "-0.388", "-0.467", "-0.531", "-0.581", "-0.613", "-0.630", "-0.630", "-0.615", "-0.586", "-0.543", "-0.489", "-0.424", "-0.352", "-0.274", "-0.193", "-0.110", "-0.027", "0.053", "0.129", "0.198", "0.260", "0.313", "0.356", "0.389", "0.411", "0.422", "0.423", "0.413", "0.393", "0.364", "0.328", "0.285", "0.236", "0.184", "0.129", "0.073", "0.018", "-0.035", "-0.086", "-0.133", "-0.174", "-0.210", "-0.239", "-0.261", "-0.276", "-0.283", "-0.283", "-0.277", "-0.263", "-0.244", "-0.220", "-0.191", "-0.158", "-0.123", "-0.087", "-0.049", "-0.012", "0.024", "0.058", "0.089", "0.117", "0.141", "0.160", "0.175", "0.185", "0.190", "0.190", "0.185", "0.176", "0.164", "0.147", "0.128", "0.106", "0.083", "0.058", "0.033", "0.008", "-0.016", "-0.039", "-0.060", "-0.078", "-0.094", "-0.107", "-0.117", "-0.124", "-0.127", "-0.127", "-0.124", "-0.118", "-0.110", "-0.099", "-0.086", "-0.071", "-0.055", "-0.039", "-0.022", "-0.005", "0.011", "0.026", "0.040", "0.052", "0.063", "0.072", "0.079", "0.083", "0.085", "0.085", "0.083", "0.079", "0.074", "0.066", "0.057", "0.048", "0.037", "0.026", "0.015", "0.004", "-0.007", "-0.017", "-0.027", "-0.035", "-0.042", "-0.048", "-0.053", "-0.056", "-0.057", "-0.057", "-0.056", "-0.053", "-0.049", "-0.044", "-0.039", "-0.032", "-0.025", "-0.017", "-0.010", "-0.002", "0.005", "0.012", "0.018", "0.024", "0.028", "0.032", "0.035", "0.037", "0.038", "0.038", "0.037", "0.036", "0.033", "0.030", "0.026", "0.021", "0.017", "0.012", "0.007", "0.002", "-0.003", "-0.008", "-0.012", "-0.016", "-0.019", "-0.022"], "name": "Desert Grey", "type": "bar", "marker": {"line": {"color": "rgb(27, 27, 27)"}, "color": "rgb(67, 67, 67)"}}, {"x": ["0.000", "0.100", "0.200", "0.300", "0.400", "0.500", "0.600", "0.700", "0.800", "0.900", "1.000", "1.100", "1.200", "1.300", "1.400", "1.500", "1.600", "1.700", "1.800", "1.900", "2.000", "2.100", "2.200", "2.300", "2.400", "2.500", "2.600", "2.700", "2.800", "2.900", "3.000", "3.100", "3.200", "3.300", "3.400", "3.500", "3.600", "3.700", "3.800", "3.900", "4.000", "4.100", "4.200", "4.300", "4.400", "4.500", "4.600", "4.700", "4.800", "4.900", "5.000", "5.100", "5.200", "5.300", "5.400", "5.500", "5.600", "5.700", "5.800", "5.900", "6.000", "6.100", "6.200", "6.300", "6.400", "6.500", "6.600", "6.700", "6.800", "6.900", "7.000", "7.100", "7.200", "7.300", "7.400", "7.500", "7.600", "7.700", "7.800", "7.900", "8.000", "8.100", "8.200", "8.300", "8.400", "8.500", "8.600", "8.700", "8.800", "8.900", "9.000", "9.100", "9.200", "9.300", "9.400", "9.500", "9.600", "9.700", "9.800", "9.900", "10.000", "10.100", "10.200", "10.300", "10.400", "10.500", "10.600", "10.700", "10.800", "10.900", "11.000", "11.100", "11.200", "11.300", "11.400", "11.500", "11.600", "11.700", "11.800", "11.900", "12.000", "12.100", "12.200", "12.300", "12.400", "12.500", "12.600", "12.700", "12.800", "12.900", "13.000", "13.100", "13.200", "13.300", "13.400", "13.500", "13.600", "13.700", "13.800", "13.900", "14.000", "14.100", "14.200", "14.300", "14.400", "14.500", "14.600", "14.700", "14.800", "14.900", "15.000", "15.100", "15.200", "15.300", "15.400", "15.500", "15.600", "15.700", "15.800", "15.900", "16.000", "16.100", "16.200", "16.300", "16.400", "16.500", "16.600", "16.700", "16.800", "16.900", "17.000", "17.100", "17.200", "17.300", "17.400", "17.500", "17.600", "17.700", "17.800", "17.900"], "y": ["0.866", "0.762", "0.643", "0.513", "0.375", "0.234", "0.093", "-0.045", "-0.177", "-0.299", "-0.409", "-0.505", "-0.585", "-0.647", "-0.690", "-0.716", "-0.722", "-0.711", "-0.682", "-0.638", "-0.581", "-0.511", "-0.431", "-0.344", "-0.252", "-0.157", "-0.062", "0.030", "0.119", "0.201", "0.274", "0.339", "0.392", "0.433", "0.463", "0.480", "0.484", "0.476", "0.457", "0.428", "0.389", "0.342", "0.289", "0.230", "0.169", "0.105", "0.042", "-0.020", "-0.080", "-0.134", "-0.184", "-0.227", "-0.263", "-0.291", "-0.310", "-0.322", "-0.324", "-0.319", "-0.307", "-0.287", "-0.261", "-0.229", "-0.194", "-0.154", "-0.113", "-0.071", "-0.028", "0.014", "0.053", "0.090", "0.123", "0.152", "0.176", "0.195", "0.208", "0.216", "0.218", "0.214", "0.206", "0.192", "0.175", "0.154", "0.130", "0.104", "0.076", "0.047", "0.019", "-0.009", "-0.036", "-0.060", "-0.083", "-0.102", "-0.118", "-0.131", "-0.139", "-0.144", "-0.146", "-0.144", "-0.138", "-0.129", "-0.117", "-0.103", "-0.087", "-0.069", "-0.051", "-0.032", "-0.013", "0.006", "0.024", "0.041", "0.055", "0.068", "0.079", "0.088", "0.093", "0.097", "0.098", "0.096", "0.092", "0.086", "0.079", "0.069", "0.058", "0.047", "0.034", "0.021", "0.008", "-0.004", "-0.016", "-0.027", "-0.037", "-0.046", "-0.053", "-0.059", "-0.063", "-0.065", "-0.066", "-0.064", "-0.062", "-0.058", "-0.053", "-0.046", "-0.039", "-0.031", "-0.023", "-0.014", "-0.006", "0.003", "0.011", "0.018", "0.025", "0.031", "0.036", "0.039", "0.042", "0.044", "0.044", "0.043", "0.041", "0.039", "0.035", "0.031", "0.026", "0.021", "0.015", "0.010", "0.004", "-0.002", "-0.007", "-0.012", "-0.017", "-0.021", "-0.024", "-0.026", "-0.028", "-0.029", "-0.029", "-0.029", "-0.028", "-0.026"], "name": "Nabokov Sky", "type": "bar", "marker": {"color": "rgb(77, 147, 209)"}}], "layout": {"font": {"size": 12, "color": "#000", "family": "Arial, sans-serif"}, "title": {"font": {"family": "Arial, sans-serif"}, "text": "Stacked Bar Chart"}, "width": 800, "xaxis": {"type": "linear", "dtick": 2, "range": [0, 12], "tick0": 0, "ticks": "", "title": {"font": {"family": "Arial, sans-serif"}, "text": ""}, "anchor": "y", "domain": [0, 1], "showgrid": true, "showline": false, "tickfont": {"family": "Arial, sans-serif"}, "zeroline": false, "autorange": false, "gridcolor": "#ddd", "gridwidth": 1, "tickangle": 0, "showexponent": "all", "exponentformat": "e", "showticklabels": true}, "yaxis": {"type": "linear", "dtick": 0.5, "range": [-1.4355555555555557, 2.0555555555555554], "tick0": 0, "ticks": "", "title": {"font": {"family": "Arial, sans-serif"}, "text": ""}, "anchor": "x", "domain": [0, 1], "showgrid": true, "showline": false, "tickfont": {"family": "Arial, sans-serif"}, "zeroline": false, "autorange": true, "gridcolor": "#ddd", "gridwidth": 1, "tickangle": 0, "showexponent": "all", "exponentformat": "e", "showticklabels": true}, "bargap": 0.2, "height": 440, "legend": {"x": 0.804493731918997, "y": 0.9711504424778762, "font": {"family": "Arial, sans-serif"}, "bgcolor": "rgba(255, 255, 255, 0)", "xanchor": "auto", "yanchor": "auto", "traceorder": "normal", "bordercolor": "rgba(0, 0, 0, 0)", "borderwidth": 1}, "margin": {"b": 60, "l": 70, "r": 40, "t": 60, "pad": 2, "autoexpand": true}, "barmode": "stack", "autosize": false, "dragmode": "zoom", "hovermode": "x", "separators": ".,", "showlegend": true, "bargroupgap": 0, "hidesources": false, "plot_bgcolor": "#fff", "paper_bgcolor": "#fff"}}}}', '{"type": "object", "title": "Plotly Example Object", "required": ["name"], "properties": {"name": {"type": "text", "title": "Object Name"}, "plot1": {"type": "plotly_chart", "title": "Example Plot 1"}}, "propertyOrder": ["name", "plot1"]}', 3, '2021-07-02 08:29:29.048965');
INSERT INTO public.objects_current VALUES (10, 0, 13, '{"name": {"text": "Plotly Array Example", "_type": "text"}, "plotlist": [{"_type": "plotly_chart", "plotly": {"data": [{"x": ["0.000", "0.100", "0.200", "0.300", "0.400", "0.500", "0.550", "0.600", "0.700", "0.800", "0.900", "1.000", "1.100", "1.200", "1.300", "1.400", "1.500", "1.600", "1.700", "1.800", "1.900", "2.000", "2.100", "2.200", "2.300", "2.400", "2.500", "2.600", "2.700", "2.800", "2.900", "3.000", "3.100", "3.200", "3.300", "3.400", "3.500", "3.600", "3.700", "3.800", "3.900", "4.000", "4.100", "4.200", "4.300", "4.400", "4.500", "4.600", "4.700", "4.800", "4.900", "5.000", "5.100", "5.200", "5.300", "5.400", "5.500", "5.600", "5.700", "5.800", "5.900", "6.000", "6.100", "6.200", "6.300", "6.400", "6.500", "6.600", "6.700", "6.800", "6.900", "7.000", "7.100", "7.200", "7.300", "7.400", "7.500", "7.600", "7.700", "7.800", "7.900", "8.000", "8.100", "8.200", "8.300", "8.400", "8.500", "8.600", "8.700", "8.800", "8.900", "9.000", "9.100", "9.200", "9.300", "9.400", "9.500", "9.600", "9.700", "9.800", "9.900", "10.000", "10.100", "10.200", "10.300", "10.400", "10.500", "10.600", "10.700", "10.800", "10.900", "11.000", "11.100", "11.200", "11.300", "11.400", "11.500", "11.600", "11.700", "11.800", "11.900", "12.000", "12.100", "12.200", "12.300", "12.400", "12.500", "12.600", "12.700", "12.800", "12.900", "13.000", "13.100", "13.200", "13.300", "13.400", "13.500", "13.600", "13.700", "13.800", "13.900", "14.000", "14.100", "14.200", "14.300", "14.400", "14.500", "14.600", "14.700", "14.800", "14.900", "15.000", "15.100", "15.200", "15.300", "15.400", "15.500", "15.600", "15.700", "15.800", "15.900", "16.000", "16.100", "16.200", "16.300", "16.400", "16.500", "16.600", "16.700", "16.800", "16.900", "17.000", "17.100", "17.200", "17.300", "17.400", "17.500", "17.600", "17.700", "17.800", "17.900"], "y": ["0.000", "0.153", "0.297", "0.428", "0.543", "0.640", "0.718", "0.775", "0.810", "0.825", "0.819", "0.793", "0.748", "0.687", "0.611", "0.524", "0.427", "0.323", "0.216", "0.107", "0.000", "-0.103", "-0.199", "-0.287", "-0.364", "-0.429", "-0.481", "-0.519", "-0.543", "-0.553", "-0.549", "-0.531", "-0.501", "-0.461", "-0.410", "-0.351", "-0.286", "-0.217", "-0.145", "-0.072", "0.000", "0.069", "0.133", "0.192", "0.244", "0.287", "0.322", "0.348", "0.364", "0.371", "0.368", "0.356", "0.336", "0.309", "0.275", "0.235", "0.192", "0.145", "0.097", "0.048", "0.000", "-0.046", "-0.089", "-0.129", "-0.163", "-0.193", "-0.216", "-0.233", "-0.244", "-0.248", "-0.247", "-0.239", "-0.225", "-0.207", "-0.184", "-0.158", "-0.129", "-0.097", "-0.065", "-0.032", "0.000", "0.031", "0.060", "0.086", "0.110", "0.129", "0.145", "0.156", "0.164", "0.167", "0.165", "0.160", "0.151", "0.139", "0.123", "0.106", "0.086", "0.065", "0.044", "0.022", "0.000", "-0.021", "-0.040", "-0.058", "-0.073", "-0.087", "-0.097", "-0.105", "-0.110", "-0.112", "-0.111", "-0.107", "-0.101", "-0.093", "-0.083", "-0.071", "-0.058", "-0.044", "-0.029", "-0.014", "0.000", "0.014", "0.027", "0.039", "0.049", "0.058", "0.065", "0.070", "0.074", "0.075", "0.074", "0.072", "0.068", "0.062", "0.055", "0.048", "0.039", "0.029", "0.020", "0.010", "0.000", "-0.009", "-0.018", "-0.026", "-0.033", "-0.039", "-0.044", "-0.047", "-0.049", "-0.050", "-0.050", "-0.048", "-0.045", "-0.042", "-0.037", "-0.032", "-0.026", "-0.020", "-0.013", "-0.007", "0.000", "0.006", "0.012", "0.017", "0.022", "0.026", "0.029", "0.032", "0.033", "0.034", "0.033", "0.032", "0.030", "0.028", "0.025", "0.021", "0.017", "0.013", "0.009", "0.004"], "name": "Emerald Blue", "type": "bar", "marker": {"color": "rgb(0, 0, 238)"}}, {"x": ["0.000", "0.100", "0.200", "0.300", "0.400", "0.500", "0.600", "0.700", "0.800", "0.900", "1.000", "1.100", "1.200", "1.300", "1.400", "1.500", "1.600", "1.700", "1.800", "1.900", "2.000", "2.100", "2.200", "2.300", "2.400", "2.500", "2.600", "2.700", "2.800", "2.900", "3.000", "3.100", "3.200", "3.300", "3.400", "3.500", "3.600", "3.700", "3.800", "3.900", "4.000", "4.100", "4.200", "4.300", "4.400", "4.500", "4.600", "4.700", "4.800", "4.900", "5.000", "5.100", "5.200", "5.300", "5.400", "5.500", "5.600", "5.700", "5.800", "5.900", "6.000", "6.100", "6.200", "6.300", "6.400", "6.500", "6.600", "6.700", "6.800", "6.900", "7.000", "7.100", "7.200", "7.300", "7.400", "7.500", "7.600", "7.700", "7.800", "7.900", "8.000", "8.100", "8.200", "8.300", "8.400", "8.500", "8.600", "8.700", "8.800", "8.900", "9.000", "9.100", "9.200", "9.300", "9.400", "9.500", "9.600", "9.700", "9.800", "9.900", "10.000", "10.100", "10.200", "10.300", "10.400", "10.500", "10.600", "10.700", "10.800", "10.900", "11.000", "11.100", "11.200", "11.300", "11.400", "11.500", "11.600", "11.700", "11.800", "11.900", "12.000", "12.100", "12.200", "12.300", "12.400", "12.500", "12.600", "12.700", "12.800", "12.900", "13.000", "13.100", "13.200", "13.300", "13.400", "13.500", "13.600", "13.700", "13.800", "13.900", "14.000", "14.100", "14.200", "14.300", "14.400", "14.500", "14.600", "14.700", "14.800", "14.900", "15.000", "15.100", "15.200", "15.300", "15.400", "15.500", "15.600", "15.700", "15.800", "15.900", "16.000", "16.100", "16.200", "16.300", "16.400", "16.500", "16.600", "16.700", "16.800", "16.900", "17.000", "17.100", "17.200", "17.300", "17.400", "17.500", "17.600", "17.700", "17.800", "17.900"], "y": ["0.866888888888888888888888888888888888888888888888888888888888888888888888888888", "0.915", "0.940", "0.940", "0.918", "0.874", "0.810", "0.729", "0.633", "0.526", "0.409", "0.288", "0.164", "0.040", "-0.079", "-0.192", "-0.295", "-0.388", "-0.467", "-0.531", "-0.581", "-0.613", "-0.630", "-0.630", "-0.615", "-0.586", "-0.543", "-0.489", "-0.424", "-0.352", "-0.274", "-0.193", "-0.110", "-0.027", "0.053", "0.129", "0.198", "0.260", "0.313", "0.356", "0.389", "0.411", "0.422", "0.423", "0.413", "0.393", "0.364", "0.328", "0.285", "0.236", "0.184", "0.129", "0.073", "0.018", "-0.035", "-0.086", "-0.133", "-0.174", "-0.210", "-0.239", "-0.261", "-0.276", "-0.283", "-0.283", "-0.277", "-0.263", "-0.244", "-0.220", "-0.191", "-0.158", "-0.123", "-0.087", "-0.049", "-0.012", "0.024", "0.058", "0.089", "0.117", "0.141", "0.160", "0.175", "0.185", "0.190", "0.190", "0.185", "0.176", "0.164", "0.147", "0.128", "0.106", "0.083", "0.058", "0.033", "0.008", "-0.016", "-0.039", "-0.060", "-0.078", "-0.094", "-0.107", "-0.117", "-0.124", "-0.127", "-0.127", "-0.124", "-0.118", "-0.110", "-0.099", "-0.086", "-0.071", "-0.055", "-0.039", "-0.022", "-0.005", "0.011", "0.026", "0.040", "0.052", "0.063", "0.072", "0.079", "0.083", "0.085", "0.085", "0.083", "0.079", "0.074", "0.066", "0.057", "0.048", "0.037", "0.026", "0.015", "0.004", "-0.007", "-0.017", "-0.027", "-0.035", "-0.042", "-0.048", "-0.053", "-0.056", "-0.057", "-0.057", "-0.056", "-0.053", "-0.049", "-0.044", "-0.039", "-0.032", "-0.025", "-0.017", "-0.010", "-0.002", "0.005", "0.012", "0.018", "0.024", "0.028", "0.032", "0.035", "0.037", "0.038", "0.038", "0.037", "0.036", "0.033", "0.030", "0.026", "0.021", "0.017", "0.012", "0.007", "0.002", "-0.003", "-0.008", "-0.012", "-0.016", "-0.019", "-0.022"], "name": "Desert Grey", "type": "bar", "marker": {"line": {"color": "rgb(27, 27, 27)"}, "color": "rgb(67, 67, 67)"}}, {"x": ["0.000", "0.100", "0.200", "0.300", "0.400", "0.500", "0.600", "0.700", "0.800", "0.900", "1.000", "1.100", "1.200", "1.300", "1.400", "1.500", "1.600", "1.700", "1.800", "1.900", "2.000", "2.100", "2.200", "2.300", "2.400", "2.500", "2.600", "2.700", "2.800", "2.900", "3.000", "3.100", "3.200", "3.300", "3.400", "3.500", "3.600", "3.700", "3.800", "3.900", "4.000", "4.100", "4.200", "4.300", "4.400", "4.500", "4.600", "4.700", "4.800", "4.900", "5.000", "5.100", "5.200", "5.300", "5.400", "5.500", "5.600", "5.700", "5.800", "5.900", "6.000", "6.100", "6.200", "6.300", "6.400", "6.500", "6.600", "6.700", "6.800", "6.900", "7.000", "7.100", "7.200", "7.300", "7.400", "7.500", "7.600", "7.700", "7.800", "7.900", "8.000", "8.100", "8.200", "8.300", "8.400", "8.500", "8.600", "8.700", "8.800", "8.900", "9.000", "9.100", "9.200", "9.300", "9.400", "9.500", "9.600", "9.700", "9.800", "9.900", "10.000", "10.100", "10.200", "10.300", "10.400", "10.500", "10.600", "10.700", "10.800", "10.900", "11.000", "11.100", "11.200", "11.300", "11.400", "11.500", "11.600", "11.700", "11.800", "11.900", "12.000", "12.100", "12.200", "12.300", "12.400", "12.500", "12.600", "12.700", "12.800", "12.900", "13.000", "13.100", "13.200", "13.300", "13.400", "13.500", "13.600", "13.700", "13.800", "13.900", "14.000", "14.100", "14.200", "14.300", "14.400", "14.500", "14.600", "14.700", "14.800", "14.900", "15.000", "15.100", "15.200", "15.300", "15.400", "15.500", "15.600", "15.700", "15.800", "15.900", "16.000", "16.100", "16.200", "16.300", "16.400", "16.500", "16.600", "16.700", "16.800", "16.900", "17.000", "17.100", "17.200", "17.300", "17.400", "17.500", "17.600", "17.700", "17.800", "17.900"], "y": ["0.866", "0.762", "0.643", "0.513", "0.375", "0.234", "0.093", "-0.045", "-0.177", "-0.299", "-0.409", "-0.505", "-0.585", "-0.647", "-0.690", "-0.716", "-0.722", "-0.711", "-0.682", "-0.638", "-0.581", "-0.511", "-0.431", "-0.344", "-0.252", "-0.157", "-0.062", "0.030", "0.119", "0.201", "0.274", "0.339", "0.392", "0.433", "0.463", "0.480", "0.484", "0.476", "0.457", "0.428", "0.389", "0.342", "0.289", "0.230", "0.169", "0.105", "0.042", "-0.020", "-0.080", "-0.134", "-0.184", "-0.227", "-0.263", "-0.291", "-0.310", "-0.322", "-0.324", "-0.319", "-0.307", "-0.287", "-0.261", "-0.229", "-0.194", "-0.154", "-0.113", "-0.071", "-0.028", "0.014", "0.053", "0.090", "0.123", "0.152", "0.176", "0.195", "0.208", "0.216", "0.218", "0.214", "0.206", "0.192", "0.175", "0.154", "0.130", "0.104", "0.076", "0.047", "0.019", "-0.009", "-0.036", "-0.060", "-0.083", "-0.102", "-0.118", "-0.131", "-0.139", "-0.144", "-0.146", "-0.144", "-0.138", "-0.129", "-0.117", "-0.103", "-0.087", "-0.069", "-0.051", "-0.032", "-0.013", "0.006", "0.024", "0.041", "0.055", "0.068", "0.079", "0.088", "0.093", "0.097", "0.098", "0.096", "0.092", "0.086", "0.079", "0.069", "0.058", "0.047", "0.034", "0.021", "0.008", "-0.004", "-0.016", "-0.027", "-0.037", "-0.046", "-0.053", "-0.059", "-0.063", "-0.065", "-0.066", "-0.064", "-0.062", "-0.058", "-0.053", "-0.046", "-0.039", "-0.031", "-0.023", "-0.014", "-0.006", "0.003", "0.011", "0.018", "0.025", "0.031", "0.036", "0.039", "0.042", "0.044", "0.044", "0.043", "0.041", "0.039", "0.035", "0.031", "0.026", "0.021", "0.015", "0.010", "0.004", "-0.002", "-0.007", "-0.012", "-0.017", "-0.021", "-0.024", "-0.026", "-0.028", "-0.029", "-0.029", "-0.029", "-0.028", "-0.026"], "name": "Nabokov Sky", "type": "bar", "marker": {"color": "rgb(77, 147, 209)"}}], "layout": {"font": {"size": 12, "color": "#000", "family": "Arial, sans-serif"}, "title": {"font": {"family": "Arial, sans-serif"}, "text": "Stacked Bar Chart"}, "width": 800, "xaxis": {"type": "linear", "dtick": 2, "range": [0, 12], "tick0": 0, "ticks": "", "title": {"font": {"family": "Arial, sans-serif"}, "text": ""}, "anchor": "y", "domain": [0, 1], "showgrid": true, "showline": false, "tickfont": {"family": "Arial, sans-serif"}, "zeroline": false, "autorange": false, "gridcolor": "#ddd", "gridwidth": 1, "tickangle": 0, "showexponent": "all", "exponentformat": "e", "showticklabels": true}, "yaxis": {"type": "linear", "dtick": 0.5, "range": [-1.4355555555555557, 2.0555555555555554], "tick0": 0, "ticks": "", "title": {"font": {"family": "Arial, sans-serif"}, "text": ""}, "anchor": "x", "domain": [0, 1], "showgrid": true, "showline": false, "tickfont": {"family": "Arial, sans-serif"}, "zeroline": false, "autorange": true, "gridcolor": "#ddd", "gridwidth": 1, "tickangle": 0, "showexponent": "all", "exponentformat": "e", "showticklabels": true}, "bargap": 0.2, "height": 440, "legend": {"x": 0.804493731918997, "y": 0.9711504424778762, "font": {"family": "Arial, sans-serif"}, "bgcolor": "rgba(255, 255, 255, 0)", "xanchor": "auto", "yanchor": "auto", "traceorder": "normal", "bordercolor": "rgba(0, 0, 0, 0)", "borderwidth": 1}, "margin": {"b": 60, "l": 70, "r": 40, "t": 60, "pad": 2, "autoexpand": true}, "barmode": "stack", "autosize": false, "dragmode": "zoom", "hovermode": "x", "separators": ".,", "showlegend": true, "bargroupgap": 0, "hidesources": false, "plot_bgcolor": "#fff", "paper_bgcolor": "#fff"}}}, {"_type": "plotly_chart", "plotly": {"data": [{"y": [2.143298776630495, 1.546437498536346, 3.1996026127943633, -3.2721650039744277, "-1.737862347610058582347745348344567921", -2.5941532378644188, 1.1336988134622026, 0.39713737515117814, -0.27839421470206477, 3.9406531966094187], "line": {"width": 1}, "name": "450", "type": "box", "marker": {"color": "rgb(223, 32, 190)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [-0.5513570147410131, 1.6941884418515312, -1.035989600357754, -1.6734746830784588, -0.1903379250550108, 0.42160414146603786, -0.5683499968674645, 0.7828243804727615, -2.738657648646538, -0.4024106513052623], "line": {"width": 1}, "name": "457", "type": "box", "marker": {"color": "rgb(217, 32, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [-1.3901652371943087, 2.4214887682900743, 1.147569881528752, 2.2351841831713792, -0.24820700567182885, -1.6126248595047912, -0.015222585493234297, -1.7751807888116073, 4.415229463381031, -1.4285566690889238], "line": {"width": 1}, "name": "465", "type": "box", "marker": {"color": "rgb(177, 32, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [0.4975138182534743, 1.215757991855703, -0.04780629861353569, 0.0014301521180146715, -0.011693084658796149, -2.906881977464424, 4.8510748670522705, 0.8040846867796213, -1.4106428462482774, 2.3887864346532606], "line": {"width": 1}, "name": "472", "type": "box", "marker": {"color": "rgb(137, 32, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [5.309088102098384, 1.5954979624142749, 1.1399594723769164, 1.2685192423716043, 1.9891077747658914, 4.479183247169927, -0.4656503273673507, 3.5133936404325956, 1.2851237031303082, 1.065354380602242], "line": {"width": 1}, "name": "480", "type": "box", "marker": {"color": "rgb(98, 32, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [1.793070030728234, 3.29213458092582, 2.1625259961030734, 0.9007411507925231, -0.916683837898133, 5.4977152470055, 1.6836217999830234, 3.380671777397879, 4.165609313750686, 1.0184343366894293], "line": {"width": 1}, "name": "487", "type": "box", "marker": {"color": "rgb(58, 32, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [3.235861441555429, 2.1411292546692486, 3.8381308213835887, 2.727752293571505, 4.017975902072184, 0.5695736013091188, 1.535514508643867, 1.6962832108823964, 0.28895804542641246, 2.5786826869714696], "line": {"width": 1}, "name": "495", "type": "box", "marker": {"color": "rgb(32, 45, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [-0.016115579695300752, 2.531199154443878, 2.188462171876345, 1.8555942771726135, 0.2876025775176916, 2.5299915024344273, 2.56353105045906, -0.04959351109352372, 5.0485171134766444, 2.6482490469234374], "line": {"width": 1}, "name": "503", "type": "box", "marker": {"color": "rgb(32, 85, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [2.4365302731146445, 0.7848896009704163, 0.36007001248524295, 3.357942698060853, 3.7843191029141785, 2.3943649408085133, 5.803538252311307, 3.9205732619959197, 1.1238016024864932, 0.02428909483070507], "line": {"width": 1}, "name": "510", "type": "box", "marker": {"color": "rgb(32, 124, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [4.7441997160566345, 0.7515838547336324, 1.8461593107504688, 4.937748255274713, 2.464649682835375, 3.5933123140369934, 4.568459375427043, 5.322171359439542, 0.980257484548269, 4.9888859397884975], "line": {"width": 1}, "name": "518", "type": "box", "marker": {"color": "rgb(32, 164, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [4.107617413889171, 1.823598893064229, 4.442565600424697, 4.4215444267782935, 2.3597001037476826, 1.5009649279909203, 3.428920172680855, 3.696492763065793, 1.8448075591657191, 4.674810996174651], "line": {"width": 1}, "name": "525", "type": "box", "marker": {"color": "rgb(32, 203, 223)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [3.6559413766345292, 5.218123953992757, 4.082994231037061, 4.724350438211446, 6.520301038717292, 4.0269504946482355, 2.111689104940635, 3.426173805884625, 2.4041213983920686, 3.7558771830255986], "line": {"width": 1}, "name": "533", "type": "box", "marker": {"color": "rgb(32, 223, 203)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [3.6207323323056206, 2.92217135200816, 4.457314990351299, 4.738588564045884, 2.2502191884477187, 3.0920972252203103, 1.7770707068519265, 3.082033226287514, 1.266449386074287, 6.162474112512239], "line": {"width": 1}, "name": "541", "type": "box", "marker": {"color": "rgb(32, 223, 164)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [1.2002602313809807, 4.326957937078774, 3.831624202706361, 6.470696868730711, 8.385697218240262, 3.378927427138537, 1.0100011719208175, 3.059657183194205, 3.45662135588293, 1.8005146791153082], "line": {"width": 1}, "name": "548", "type": "box", "marker": {"color": "rgb(32, 223, 124)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [3.916814324730089, 1.1822314723354634, 2.6838499750862366, 3.9047897374529525, 3.2646310457952747, 3.494345580357663, 4.85068215147808, 3.21632919185715, 4.543453196746212, 4.304948860307396], "line": {"width": 1}, "name": "556", "type": "box", "marker": {"color": "rgb(32, 223, 85)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [7.188869064393717, 2.969613080027406, 2.861887894692491, 1.9339807896829542, 5.916747428886293, 3.7862988306773264, 3.365480207639184, 4.840355678120315, 5.467164053423591, 5.102661041557068], "line": {"width": 1}, "name": "563", "type": "box", "marker": {"color": "rgb(32, 223, 45)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [2.023828346393208, 4.3933555087541585, 6.172651079392306, 3.2182077662451865, 4.890593997097495, 0.19897657320179274, 4.3726706934050625, 4.245739954374094, 3.3852788348198035, 4.873691579297628], "line": {"width": 1}, "name": "571", "type": "box", "marker": {"color": "rgb(58, 223, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [1.3883512495925547, 2.8579471237790264, 4.8663809840475984, 5.1951118805760625, 4.205722291898466, 4.5553567442938085, 6.200717614751488, 4.708467697352261, 4.357794178274319, 3.6873288890259586], "line": {"width": 1}, "name": "578", "type": "box", "marker": {"color": "rgb(98, 223, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [5.023381822090899, 2.4160739470924977, 6.839803818089738, 3.8121261015654513, 2.266919394391742, 4.223121388019584, 2.358904599837688, 5.479564877537197, 4.372792152115252, 4.078049952346909], "line": {"width": 1}, "name": "586", "type": "box", "marker": {"color": "rgb(137, 223, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [4.364265628125186, 3.637151936860906, 4.340102390620965, 3.8253415529586503, 3.84445134734876, 2.789086489665339, 2.990753771535526, 2.2238138482703986, 4.067840176264388, 3.390657214377273], "line": {"width": 1}, "name": "594", "type": "box", "marker": {"color": "rgb(177, 223, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [3.944128530705616, 4.299027748180328, 3.559320048683847, 3.953395160076097, 4.951561324824724, 0.28423798817635415, 1.703079084515436, 2.1233249084555856, 4.50899816468616, 2.90914860672678], "line": {"width": 1}, "name": "601", "type": "box", "marker": {"color": "rgb(217, 223, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [1.4987245004945127, 3.4988764107954573, 1.035666193651728, 3.698078313017795, 2.8601991008463807, 4.59108686634301, 1.6416602569201257, 2.620692910978377, 4.352271873131939, 3.387796281522468], "line": {"width": 1}, "name": "609", "type": "box", "marker": {"color": "rgb(223, 190, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [3.886588759281743, 4.09639467114146, 3.781059716978851, 3.8506624719056455, 3.2983203880390692, 2.7906038044537773, 1.9089288355943315, 3.741375625088334, 4.7920177887664, 3.8756714538590957], "line": {"width": 1}, "name": "616", "type": "box", "marker": {"color": "rgb(223, 151, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [3.7930929392545725, 2.9595815901683897, 4.278816973575015, 4.12873578159929, 3.2452722246603787, 2.2228796432055917, 3.1117613387871432, 4.700202930162271, 3.7364376410841977, 2.624246824503665], "line": {"width": 1}, "name": "624", "type": "box", "marker": {"color": "rgb(223, 111, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [2.688817168538662, 2.2647900378206796, 2.794030735666634, 2.5557136986888924, 3.2975536939952153, 1.464310183835455, 4.79675367384749, 2.721293236786012, 1.3407340944698982, 2.7925891550565827], "line": {"width": 1}, "name": "632", "type": "box", "marker": {"color": "rgb(223, 71, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [3.302664391056707, 3.8779275997242513, 2.5606073377558447, 2.172284155005903, 4.986094304920282, 2.585843158431967, 1.55578389553859, 1.9354736601919273, 1.6906489597225358, 3.8132044950220774], "line": {"width": 1}, "name": "639", "type": "box", "marker": {"color": "rgb(223, 32, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [1.2757796572946754, 3.5749547405713544, 2.213564040974323, 2.622646077414124, 1.9695916314640103, 2.237719685949837, 3.5117622169738114, 1.9529579923485183, 1.9350848528531803, 1.9228718838389787], "line": {"width": 1}, "name": "647", "type": "box", "marker": {"color": "rgb(223, 32, 32)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [2.112951496740204, 3.9406157111578675, 2.2747354097753396, 3.8932852199747097, 0.7139956340270186, 1.5278830689466767, 2.401168983865303, 3.281033802949576, 1.565578801322196, 2.7721094415950764], "line": {"width": 1}, "name": "654", "type": "box", "marker": {"color": "rgb(223, 32, 71)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [0.12123446809023997, 3.3306394911873394, 0.38816372142868594, 2.4404379445719204, 0.5699057463324029, 2.1574477293800833, 4.342293935187394, 1.126581491394398, 0.03028431816905841, -0.769753202505036], "line": {"width": 1}, "name": "662", "type": "box", "marker": {"color": "rgb(223, 32, 111)"}, "boxpoints": false, "whiskerwidth": 0.75}, {"y": [0.9002461908620343, 0.8892524414281886, 2.4450446737565454, 2.4648528013844877, 0.8404729335174261, 0.6925337622570281, 0.5882537991503783, 1.2618587377404258, 1.388487877092837, 1.565283315273657], "line": {"width": 1}, "name": "670", "type": "box", "marker": {"color": "rgb(223, 32, 151)"}, "boxpoints": false, "whiskerwidth": 0.75}], "layout": {"font": {"size": 12, "color": "rgb(67, 67, 67)", "family": "Arial, sans-serif"}, "title": {"font": {"size": 18}, "text": "Spectral<br>Box Plot"}, "width": 600, "xaxis": {"type": "category", "dtick": 1, "range": [-0.5, 29.5], "tick0": 0, "ticks": "", "title": {"text": "Wavelength (nm)"}, "anchor": "y", "domain": [0, 1], "showgrid": false, "showline": false, "zeroline": true, "autorange": true, "tickangle": 90, "zerolinecolor": "#000", "zerolinewidth": 1, "showticklabels": true}, "yaxis": {"type": "linear", "dtick": 2, "range": [-3.919824016319688, 9.033356230585522], "tick0": 0, "ticks": "", "title": {"text": "Response (mV)"}, "anchor": "x", "domain": [0, 1], "showgrid": true, "showline": false, "zeroline": false, "autorange": true, "gridcolor": "rgb(255, 255, 255)", "gridwidth": 1.5, "tickangle": 0, "showticklabels": true}, "height": 400, "margin": {"b": 70, "l": 50, "r": 20, "t": 40, "pad": 2, "autoexpand": true}, "boxmode": "overlay", "autosize": false, "dragmode": "zoom", "hovermode": "x", "separators": ".,", "showlegend": false, "hidesources": false, "plot_bgcolor": "rgb(233, 233, 233)", "paper_bgcolor": "rgb(233, 233, 233)"}}}, {"_type": "plotly_chart", "plotly": {"data": [{"z": [[1, 4, 2, 3, 1, 3, 4, 2, 3, 1, 2, 3, 4, 2, 3, 2, 3, 4, 2, 3, 4], [4, 3, 3, 4, 4, 3, 3, 9, 6, 7, 9, 4, 3, 5, 6, 5, 3, 12, 4, 6, 7, 8, 9, 3, 4, 14, 4, 2, 3, 2, 3, 4, 2, 1, 2, 3, 2, 3, 4, 2, 1], [2, 3, 2, 4, 3, 3, 4, 2, 3, 2, 3, 4, 2, 1, 3, 4, 4, 6, 3, 4, 9, 6, 7, 9, 4, 3, 5, 6, 5, 3, 12, 4, 6, 7, 8, 9, 3, 4, 14, 2, 3], [3, 9, 6, 7, 9, 4, 3, 5, 6, 5, 3, 12, 4, 6, 7, 8, 9, 3, 4, 14, 4, 2, 3, 1, 3, 4, 2, 3, 1, 2, 3, 4, 2, 3, 2, 3, 4, 2, 3, 4, 2], [4, 3, 3, 4, 4, 9, 6, 7, 9, 4, 3, 5, 6, 5, 3, 12, 4, 6, 7, 8, 9, 3, 4, 14, 3, 3, 4, 2, 3, 2, 3, 4, 2, 1, 2, 3, 2, 3, 4, 2, 1], [2, 3, 2, 4, 3, 3, 4, 2, 3, 2, 3, 4, 2, 1, 3, 4, 4, 6, 3, 4, 2, 3, 9, 6, 7, 9, 4, 3, 5, 6, 5, 3, 12, 4, 6, 7, 8, 9, 3, 4, 14], [3, 4, 2, 9, 6, 7, 9, 4, 3, 5, 6, 5, 3, 12, 4, 6, 7, 8, 9, 3, 4, 14, 3, 1, 3, 4, 2, 3, 1, 2, 3, 4, 2, 3, 2, 3, 4, 2, 3, 4, 2], [4, 3, 3, 4, 4, 3, 3, 4, 9, 6, 7, 9, 4, 3, 5, 6, 5, 3, 12, 4, 6, 7, 8, 9, 3, 4, 14, 2, 3, 2, 3, 4, 2, 1, 2, 3, 2, 3, 4, 2, 1], [2, 3, 2, 4, 3, 3, 4, 2, 3, 2, 3, 4, 2, 1, 3, 4, 4, 6, 3, 4, 2, 3, 9, 6, 7, 9, 4, 3, 5, 6, 5, 3, 12, 4, 6, 7, 8, 9, 3, 4, 14]], "dx": 5, "dy": 5, "x0": 2, "y0": 2, "name": "trace 0", "type": "heatmap", "zauto": true, "colorscale": [[0, "rgb(12,51,131)"], [0.25, "rgb(10,136,186)"], [0.5, "rgb(242,211,56)"], [0.75, "rgb(242,143,56)"], [1, "rgb(217,30,30)"]]}], "layout": {"font": {"size": 12, "color": "#000", "family": "Arial, sans-serif"}, "title": {"text": "Simple Heatmap"}, "width": 790, "xaxis": {"type": "linear", "dtick": 20, "range": [-0.5, 204.5], "tick0": 0, "ticks": "", "title": {"text": ""}, "anchor": "y", "domain": [0, 1], "showgrid": true, "showline": false, "zeroline": true, "autorange": true, "gridcolor": "#ddd", "gridwidth": 1, "rangemode": "normal", "tickangle": 0, "showexponent": "all", "zerolinecolor": "#000", "zerolinewidth": 1, "exponentformat": "e", "showticklabels": true}, "yaxis": {"type": "linear", "dtick": 5, "range": [-0.5, 44.5], "tick0": 0, "ticks": "", "title": {"text": ""}, "anchor": "x", "domain": [0, 1], "showgrid": true, "showline": false, "zeroline": true, "autorange": true, "gridcolor": "#ddd", "gridwidth": 1, "rangemode": "normal", "tickangle": 0, "showexponent": "all", "zerolinecolor": "#000", "zerolinewidth": 1, "exponentformat": "e", "showticklabels": true}, "height": 390, "margin": {"b": 60, "l": 70, "r": 200, "t": 60, "pad": 2, "autoexpand": true}, "autosize": false, "dragmode": "zoom", "hovermode": "x", "separators": ".,", "hidesources": false, "plot_bgcolor": "#fff", "paper_bgcolor": "#fff"}}}]}', '{"type": "object", "title": "Plotly Array Example Object", "required": ["name"], "properties": {"name": {"type": "text", "title": "Object Name"}, "plotlist": {"type": "array", "items": {"type": "plotly_chart", "title": "listitem"}, "style": "list", "title": "Plot List", "minItems": 1}}, "propertyOrder": ["name", "plotlist"]}', 3, '2021-07-02 08:29:29.246424');


--
-- Data for Name: objects_previous; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.objects_previous VALUES (5, 0, 10, '{"name": {"text": {"de": "Objekt 1", "en": "Object 1"}, "_type": "text"}}', '{"type": "object", "title": "Example Object", "required": ["name"], "properties": {"name": {"type": "text", "title": {"de": "Objektname", "en": "Object Name"}, "languages": "all"}, "sample": {"type": "sample", "title": {"de": "Probe", "en": "Sample"}}}}', 3, '2021-07-02 08:29:28.87222');


--
-- Data for Name: project_action_permissions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: project_invitations; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: project_object_association; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.project_object_association VALUES (1, 1);


--
-- Data for Name: project_object_permissions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.projects VALUES (1, '{"en": "Example Project", "de": "Beispielprojekt"}', '{"en": "This is an example project", "de": "Dies ist ein Beispielprojekt"}');
INSERT INTO public.projects VALUES (2, '{"en": "Example Project 2", "de": "Beispielprojekt 2"}', '{"en": "This is another example project", "de": "Dies ist ein weiteres Beispielprojekt"}');


--
-- Data for Name: public_actions; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.public_actions VALUES (1);
INSERT INTO public.public_actions VALUES (2);
INSERT INTO public.public_actions VALUES (3);
INSERT INTO public.public_actions VALUES (4);
INSERT INTO public.public_actions VALUES (5);
INSERT INTO public.public_actions VALUES (6);
INSERT INTO public.public_actions VALUES (7);
INSERT INTO public.public_actions VALUES (8);
INSERT INTO public.public_actions VALUES (9);
INSERT INTO public.public_actions VALUES (10);
INSERT INTO public.public_actions VALUES (11);
INSERT INTO public.public_actions VALUES (12);
INSERT INTO public.public_actions VALUES (13);
INSERT INTO public.public_actions VALUES (14);


--
-- Data for Name: public_objects; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.public_objects VALUES (5);
INSERT INTO public.public_objects VALUES (6);
INSERT INTO public.public_objects VALUES (7);
INSERT INTO public.public_objects VALUES (8);
INSERT INTO public.public_objects VALUES (9);
INSERT INTO public.public_objects VALUES (10);


--
-- Data for Name: settings; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: subproject_relationship; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.subproject_relationship VALUES (1, 2, true);


--
-- Data for Name: tags; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: user_action_permissions; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: user_group_memberships; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.user_group_memberships VALUES (2, 1);


--
-- Data for Name: user_invitations; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: user_log_entries; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.user_log_entries VALUES (1, 'CREATE_INSTRUMENT_LOG_ENTRY', 3, '{"instrument_id": 1, "instrument_log_entry_id": 1}', '2021-07-02 08:29:27.931387');
INSERT INTO public.user_log_entries VALUES (2, 'CREATE_INSTRUMENT_LOG_ENTRY', 3, '{"instrument_id": 1, "instrument_log_entry_id": 2}', '2021-07-02 08:29:27.965656');
INSERT INTO public.user_log_entries VALUES (3, 'CREATE_INSTRUMENT_LOG_ENTRY', 3, '{"instrument_id": 1, "instrument_log_entry_id": 3}', '2021-07-02 08:29:27.987367');
INSERT INTO public.user_log_entries VALUES (4, 'CREATE_INSTRUMENT_LOG_ENTRY', 3, '{"instrument_id": 1, "instrument_log_entry_id": 4}', '2021-07-02 08:29:28.009023');
INSERT INTO public.user_log_entries VALUES (5, 'CREATE_INSTRUMENT_LOG_ENTRY', 3, '{"instrument_id": 1, "instrument_log_entry_id": 5}', '2021-07-02 08:29:28.029853');
INSERT INTO public.user_log_entries VALUES (6, 'CREATE_INSTRUMENT_LOG_ENTRY', 3, '{"instrument_id": 1, "instrument_log_entry_id": 6}', '2021-07-02 08:29:28.048224');
INSERT INTO public.user_log_entries VALUES (7, 'CREATE_INSTRUMENT_LOG_ENTRY', 3, '{"instrument_id": 1, "instrument_log_entry_id": 7}', '2021-07-02 08:29:28.068907');
INSERT INTO public.user_log_entries VALUES (8, 'CREATE_INSTRUMENT_LOG_ENTRY', 3, '{"instrument_id": 1, "instrument_log_entry_id": 8}', '2021-07-02 08:29:28.095974');
INSERT INTO public.user_log_entries VALUES (9, 'POST_COMMENT', 2, '{"object_id": 1, "comment_id": 1}', '2021-07-02 08:29:28.428923');
INSERT INTO public.user_log_entries VALUES (10, 'POST_COMMENT', 2, '{"object_id": 1, "comment_id": 2}', '2021-07-02 08:29:28.43818');
INSERT INTO public.user_log_entries VALUES (11, 'UPLOAD_FILE', 2, '{"object_id": 1, "file_id": 0}', '2021-07-02 08:29:28.454502');
INSERT INTO public.user_log_entries VALUES (12, 'UPLOAD_FILE', 2, '{"object_id": 1, "file_id": 1}', '2021-07-02 08:29:28.465378');
INSERT INTO public.user_log_entries VALUES (13, 'UPLOAD_FILE', 2, '{"object_id": 1, "file_id": 2}', '2021-07-02 08:29:28.490378');
INSERT INTO public.user_log_entries VALUES (14, 'CREATE_OBJECT', 3, '{"object_id": 5}', '2021-07-02 08:29:28.882975');
INSERT INTO public.user_log_entries VALUES (15, 'CREATE_OBJECT', 3, '{"object_id": 6}', '2021-07-02 08:29:28.92142');
INSERT INTO public.user_log_entries VALUES (16, 'EDIT_OBJECT', 3, '{"object_id": 5, "version_id": 1}', '2021-07-02 08:29:28.955641');
INSERT INTO public.user_log_entries VALUES (17, 'CREATE_OBJECT', 3, '{"object_id": 7}', '2021-07-02 08:29:28.985652');
INSERT INTO public.user_log_entries VALUES (18, 'CREATE_OBJECT', 2, '{"object_id": 8}', '2021-07-02 08:29:29.017935');
INSERT INTO public.user_log_entries VALUES (19, 'CREATE_OBJECT', 3, '{"object_id": 9}', '2021-07-02 08:29:29.21619');
INSERT INTO public.user_log_entries VALUES (20, 'CREATE_OBJECT', 3, '{"object_id": 10}', '2021-07-02 08:29:29.307871');
INSERT INTO public.user_log_entries VALUES (21, 'CREATE_LOCATION', 2, '{"location_id": 1}', '2021-07-02 08:29:29.326245');
INSERT INTO public.user_log_entries VALUES (22, 'CREATE_LOCATION', 2, '{"location_id": 2}', '2021-07-02 08:29:29.33453');
INSERT INTO public.user_log_entries VALUES (23, 'CREATE_LOCATION', 2, '{"location_id": 3}', '2021-07-02 08:29:29.34127');
INSERT INTO public.user_log_entries VALUES (24, 'CREATE_LOCATION', 2, '{"location_id": 4}', '2021-07-02 08:29:29.347986');
INSERT INTO public.user_log_entries VALUES (25, 'ASSIGN_LOCATION', 2, '{"object_location_assignment_id": 1}', '2021-07-02 08:29:29.362402');
INSERT INTO public.user_log_entries VALUES (26, 'ASSIGN_LOCATION', 3, '{"object_location_assignment_id": 2}', '2021-07-02 08:29:29.383191');


--
-- Data for Name: user_object_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.user_object_permissions VALUES (3, 4, 'WRITE');
INSERT INTO public.user_object_permissions VALUES (5, 3, 'GRANT');
INSERT INTO public.user_object_permissions VALUES (6, 3, 'GRANT');
INSERT INTO public.user_object_permissions VALUES (7, 3, 'GRANT');
INSERT INTO public.user_object_permissions VALUES (8, 2, 'GRANT');
INSERT INTO public.user_object_permissions VALUES (9, 3, 'GRANT');
INSERT INTO public.user_object_permissions VALUES (10, 3, 'GRANT');
INSERT INTO public.user_object_permissions VALUES (4, 2, 'GRANT');


--
-- Data for Name: user_project_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.user_project_permissions VALUES (1, 2, 'GRANT');
INSERT INTO public.user_project_permissions VALUES (2, 2, 'GRANT');


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.users VALUES (1, 'admin', 'f.rhiem@fz-juelich.de', 'PERSON', true, false, false, NULL, NULL, true, NULL, '{}');
INSERT INTO public.users VALUES (2, 'Instrument Scientist', 'instrument@example.com', 'PERSON', false, false, false, NULL, NULL, true, NULL, '{}');
INSERT INTO public.users VALUES (3, 'Basic User', 'basic@example.com', 'PERSON', false, false, false, NULL, NULL, true, NULL, '{}');
INSERT INTO public.users VALUES (4, 'API User', 'api@example.com', 'OTHER', false, false, false, NULL, NULL, true, NULL, '{}');


--
-- Name: action_translations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.action_translations_id_seq', 14, true);


--
-- Name: action_type_translations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.action_type_translations_id_seq', 6, true);


--
-- Name: action_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.action_types_id_seq', 1, false);


--
-- Name: actions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.actions_id_seq', 14, true);


--
-- Name: api_log_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.api_log_entries_id_seq', 1, false);


--
-- Name: authentications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.authentications_id_seq', 2, true);


--
-- Name: comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.comments_id_seq', 2, true);


--
-- Name: file_log_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.file_log_entries_id_seq', 2, true);


--
-- Name: group_invitations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.group_invitations_id_seq', 1, false);


--
-- Name: groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.groups_id_seq', 1, true);


--
-- Name: instrument_log_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.instrument_log_categories_id_seq', 5, true);


--
-- Name: instrument_log_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.instrument_log_entries_id_seq', 8, true);


--
-- Name: instrument_log_file_attachments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.instrument_log_file_attachments_id_seq', 3, true);


--
-- Name: instrument_log_object_attachments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.instrument_log_object_attachments_id_seq', 10, true);


--
-- Name: instrument_translations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.instrument_translations_id_seq', 6, true);


--
-- Name: instruments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.instruments_id_seq', 5, true);


--
-- Name: languages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.languages_id_seq', 1, false);


--
-- Name: locations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.locations_id_seq', 4, true);


--
-- Name: markdown_to_html_cache_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.markdown_to_html_cache_entries_id_seq', 1, false);


--
-- Name: notification_mode_for_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notification_mode_for_types_id_seq', 1, false);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notifications_id_seq', 11, true);


--
-- Name: object_location_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.object_location_assignments_id_seq', 2, true);


--
-- Name: object_log_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.object_log_entries_id_seq', 23, true);


--
-- Name: objects_current_object_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.objects_current_object_id_seq', 10, true);


--
-- Name: project_invitations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.project_invitations_id_seq', 1, false);


--
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.projects_id_seq', 2, true);


--
-- Name: tags_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tags_id_seq', 1, false);


--
-- Name: user_invitations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_invitations_id_seq', 1, false);


--
-- Name: user_log_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_log_entries_id_seq', 26, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 4, true);


--
-- Name: action_translations _language_id_action_id_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_translations
    ADD CONSTRAINT _language_id_action_id_uc UNIQUE (language_id, action_id);


--
-- Name: action_type_translations _language_id_action_type_id_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_type_translations
    ADD CONSTRAINT _language_id_action_type_id_uc UNIQUE (language_id, action_type_id);


--
-- Name: instrument_translations _language_id_instrument_id_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_translations
    ADD CONSTRAINT _language_id_instrument_id_uc UNIQUE (language_id, instrument_id);


--
-- Name: notification_mode_for_types _notification_mode_for_types_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_mode_for_types
    ADD CONSTRAINT _notification_mode_for_types_uc UNIQUE (type, user_id);


--
-- Name: action_translations action_translations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_translations
    ADD CONSTRAINT action_translations_pkey PRIMARY KEY (id);


--
-- Name: action_type_translations action_type_translations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_type_translations
    ADD CONSTRAINT action_type_translations_pkey PRIMARY KEY (id);


--
-- Name: action_types action_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_types
    ADD CONSTRAINT action_types_pkey PRIMARY KEY (id);


--
-- Name: actions actions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT actions_pkey PRIMARY KEY (id);


--
-- Name: api_log_entries api_log_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_log_entries
    ADD CONSTRAINT api_log_entries_pkey PRIMARY KEY (id);


--
-- Name: authentications authentications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authentications
    ADD CONSTRAINT authentications_pkey PRIMARY KEY (id);


--
-- Name: comments comments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_pkey PRIMARY KEY (id);


--
-- Name: dataverse_exports dataverse_exports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataverse_exports
    ADD CONSTRAINT dataverse_exports_pkey PRIMARY KEY (object_id);


--
-- Name: default_group_permissions default_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_group_permissions
    ADD CONSTRAINT default_group_permissions_pkey PRIMARY KEY (creator_id, group_id);


--
-- Name: default_project_permissions default_project_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_project_permissions
    ADD CONSTRAINT default_project_permissions_pkey PRIMARY KEY (creator_id, project_id);


--
-- Name: default_public_permissions default_public_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_public_permissions
    ADD CONSTRAINT default_public_permissions_pkey PRIMARY KEY (creator_id);


--
-- Name: default_user_permissions default_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_user_permissions
    ADD CONSTRAINT default_user_permissions_pkey PRIMARY KEY (creator_id, user_id);


--
-- Name: favorite_actions favorite_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.favorite_actions
    ADD CONSTRAINT favorite_actions_pkey PRIMARY KEY (action_id, user_id);


--
-- Name: favorite_instruments favorite_instruments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.favorite_instruments
    ADD CONSTRAINT favorite_instruments_pkey PRIMARY KEY (instrument_id, user_id);


--
-- Name: file_log_entries file_log_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_log_entries
    ADD CONSTRAINT file_log_entries_pkey PRIMARY KEY (id);


--
-- Name: files files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_pkey PRIMARY KEY (id, object_id);


--
-- Name: group_action_permissions group_action_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_action_permissions
    ADD CONSTRAINT group_action_permissions_pkey PRIMARY KEY (action_id, group_id);


--
-- Name: group_invitations group_invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_invitations
    ADD CONSTRAINT group_invitations_pkey PRIMARY KEY (id);


--
-- Name: group_object_permissions group_object_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_object_permissions
    ADD CONSTRAINT group_object_permissions_pkey PRIMARY KEY (object_id, group_id);


--
-- Name: group_project_permissions group_project_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_project_permissions
    ADD CONSTRAINT group_project_permissions_pkey PRIMARY KEY (project_id, group_id);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: instrument_log_categories instrument_log_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_categories
    ADD CONSTRAINT instrument_log_categories_pkey PRIMARY KEY (id);


--
-- Name: instrument_log_entries instrument_log_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_entries
    ADD CONSTRAINT instrument_log_entries_pkey PRIMARY KEY (id);


--
-- Name: instrument_log_entry_versions instrument_log_entry_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_entry_versions
    ADD CONSTRAINT instrument_log_entry_versions_pkey PRIMARY KEY (log_entry_id, version_id);


--
-- Name: instrument_log_file_attachments instrument_log_file_attachments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_file_attachments
    ADD CONSTRAINT instrument_log_file_attachments_pkey PRIMARY KEY (id);


--
-- Name: instrument_log_object_attachments instrument_log_object_attachments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_object_attachments
    ADD CONSTRAINT instrument_log_object_attachments_pkey PRIMARY KEY (id);


--
-- Name: instrument_translations instrument_translations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_translations
    ADD CONSTRAINT instrument_translations_pkey PRIMARY KEY (id);


--
-- Name: instruments instruments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instruments
    ADD CONSTRAINT instruments_pkey PRIMARY KEY (id);


--
-- Name: languages languages_lang_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.languages
    ADD CONSTRAINT languages_lang_code_key UNIQUE (lang_code);


--
-- Name: languages languages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.languages
    ADD CONSTRAINT languages_pkey PRIMARY KEY (id);


--
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (id);


--
-- Name: markdown_images markdown_images_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.markdown_images
    ADD CONSTRAINT markdown_images_pkey PRIMARY KEY (file_name);


--
-- Name: markdown_to_html_cache_entries markdown_to_html_cache_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.markdown_to_html_cache_entries
    ADD CONSTRAINT markdown_to_html_cache_entries_pkey PRIMARY KEY (id);


--
-- Name: notification_mode_for_types notification_mode_for_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_mode_for_types
    ADD CONSTRAINT notification_mode_for_types_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: object_location_assignments object_location_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_location_assignments
    ADD CONSTRAINT object_location_assignments_pkey PRIMARY KEY (id);


--
-- Name: object_log_entries object_log_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_log_entries
    ADD CONSTRAINT object_log_entries_pkey PRIMARY KEY (id);


--
-- Name: object_publications object_publications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_publications
    ADD CONSTRAINT object_publications_pkey PRIMARY KEY (object_id, doi);


--
-- Name: objects_current objects_current_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.objects_current
    ADD CONSTRAINT objects_current_pkey PRIMARY KEY (object_id);


--
-- Name: objects_previous objects_previous_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.objects_previous
    ADD CONSTRAINT objects_previous_pkey PRIMARY KEY (object_id, version_id);


--
-- Name: project_action_permissions project_action_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_action_permissions
    ADD CONSTRAINT project_action_permissions_pkey PRIMARY KEY (action_id, project_id);


--
-- Name: project_invitations project_invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_pkey PRIMARY KEY (id);


--
-- Name: project_object_association project_object_association_object_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_object_association
    ADD CONSTRAINT project_object_association_object_id_key UNIQUE (object_id);


--
-- Name: project_object_association project_object_association_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_object_association
    ADD CONSTRAINT project_object_association_pkey PRIMARY KEY (project_id);


--
-- Name: project_object_permissions project_object_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_object_permissions
    ADD CONSTRAINT project_object_permissions_pkey PRIMARY KEY (object_id, project_id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: public_actions public_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.public_actions
    ADD CONSTRAINT public_actions_pkey PRIMARY KEY (action_id);


--
-- Name: public_objects public_objects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.public_objects
    ADD CONSTRAINT public_objects_pkey PRIMARY KEY (object_id);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (user_id);


--
-- Name: subproject_relationship subproject_relationship_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subproject_relationship
    ADD CONSTRAINT subproject_relationship_pkey PRIMARY KEY (parent_project_id, child_project_id);


--
-- Name: tags tags_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_name_key UNIQUE (name);


--
-- Name: tags tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_pkey PRIMARY KEY (id);


--
-- Name: user_action_permissions user_action_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_action_permissions
    ADD CONSTRAINT user_action_permissions_pkey PRIMARY KEY (action_id, user_id);


--
-- Name: user_invitations user_invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_invitations
    ADD CONSTRAINT user_invitations_pkey PRIMARY KEY (id);


--
-- Name: user_log_entries user_log_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_log_entries
    ADD CONSTRAINT user_log_entries_pkey PRIMARY KEY (id);


--
-- Name: user_object_permissions user_object_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_object_permissions
    ADD CONSTRAINT user_object_permissions_pkey PRIMARY KEY (object_id, user_id);


--
-- Name: user_project_permissions user_project_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_project_permissions
    ADD CONSTRAINT user_project_permissions_pkey PRIMARY KEY (project_id, user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: action_translations action_translations_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_translations
    ADD CONSTRAINT action_translations_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id);


--
-- Name: action_translations action_translations_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_translations
    ADD CONSTRAINT action_translations_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id);


--
-- Name: action_type_translations action_type_translations_action_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_type_translations
    ADD CONSTRAINT action_type_translations_action_type_id_fkey FOREIGN KEY (action_type_id) REFERENCES public.action_types(id);


--
-- Name: action_type_translations action_type_translations_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_type_translations
    ADD CONSTRAINT action_type_translations_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id);


--
-- Name: actions actions_instrument_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT actions_instrument_id_fkey FOREIGN KEY (instrument_id) REFERENCES public.instruments(id);


--
-- Name: actions actions_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT actions_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.action_types(id);


--
-- Name: actions actions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT actions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: api_log_entries api_log_entries_api_token_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_log_entries
    ADD CONSTRAINT api_log_entries_api_token_id_fkey FOREIGN KEY (api_token_id) REFERENCES public.authentications(id);


--
-- Name: association association_instrument_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.association
    ADD CONSTRAINT association_instrument_id_fkey FOREIGN KEY (instrument_id) REFERENCES public.instruments(id);


--
-- Name: association association_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.association
    ADD CONSTRAINT association_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: authentications authentications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authentications
    ADD CONSTRAINT authentications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: comments comments_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: comments comments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: dataverse_exports dataverse_exports_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataverse_exports
    ADD CONSTRAINT dataverse_exports_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: dataverse_exports dataverse_exports_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataverse_exports
    ADD CONSTRAINT dataverse_exports_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: default_group_permissions default_group_permissions_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_group_permissions
    ADD CONSTRAINT default_group_permissions_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id);


--
-- Name: default_group_permissions default_group_permissions_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_group_permissions
    ADD CONSTRAINT default_group_permissions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: default_project_permissions default_project_permissions_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_project_permissions
    ADD CONSTRAINT default_project_permissions_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id);


--
-- Name: default_project_permissions default_project_permissions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_project_permissions
    ADD CONSTRAINT default_project_permissions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: default_public_permissions default_public_permissions_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_public_permissions
    ADD CONSTRAINT default_public_permissions_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id);


--
-- Name: default_user_permissions default_user_permissions_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_user_permissions
    ADD CONSTRAINT default_user_permissions_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id);


--
-- Name: default_user_permissions default_user_permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.default_user_permissions
    ADD CONSTRAINT default_user_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: favorite_actions favorite_actions_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.favorite_actions
    ADD CONSTRAINT favorite_actions_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id);


--
-- Name: favorite_actions favorite_actions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.favorite_actions
    ADD CONSTRAINT favorite_actions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: favorite_instruments favorite_instruments_instrument_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.favorite_instruments
    ADD CONSTRAINT favorite_instruments_instrument_id_fkey FOREIGN KEY (instrument_id) REFERENCES public.instruments(id);


--
-- Name: favorite_instruments favorite_instruments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.favorite_instruments
    ADD CONSTRAINT favorite_instruments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: file_log_entries file_log_entries_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_log_entries
    ADD CONSTRAINT file_log_entries_object_id_fkey FOREIGN KEY (object_id, file_id) REFERENCES public.files(object_id, id);


--
-- Name: file_log_entries file_log_entries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_log_entries
    ADD CONSTRAINT file_log_entries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: files files_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: files files_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: group_action_permissions group_action_permissions_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_action_permissions
    ADD CONSTRAINT group_action_permissions_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id);


--
-- Name: group_action_permissions group_action_permissions_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_action_permissions
    ADD CONSTRAINT group_action_permissions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_invitations group_invitations_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_invitations
    ADD CONSTRAINT group_invitations_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_invitations group_invitations_inviter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_invitations
    ADD CONSTRAINT group_invitations_inviter_id_fkey FOREIGN KEY (inviter_id) REFERENCES public.users(id);


--
-- Name: group_invitations group_invitations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_invitations
    ADD CONSTRAINT group_invitations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: group_object_permissions group_object_permissions_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_object_permissions
    ADD CONSTRAINT group_object_permissions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_object_permissions group_object_permissions_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_object_permissions
    ADD CONSTRAINT group_object_permissions_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: group_project_permissions group_project_permissions_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_project_permissions
    ADD CONSTRAINT group_project_permissions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_project_permissions group_project_permissions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_project_permissions
    ADD CONSTRAINT group_project_permissions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: instrument_log_categories instrument_log_categories_instrument_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_categories
    ADD CONSTRAINT instrument_log_categories_instrument_id_fkey FOREIGN KEY (instrument_id) REFERENCES public.instruments(id);


--
-- Name: instrument_log_entries instrument_log_entries_instrument_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_entries
    ADD CONSTRAINT instrument_log_entries_instrument_id_fkey FOREIGN KEY (instrument_id) REFERENCES public.instruments(id);


--
-- Name: instrument_log_entries instrument_log_entries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_entries
    ADD CONSTRAINT instrument_log_entries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: instrument_log_entry_version_category_associations instrument_log_entry_version_category_associa_log_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_entry_version_category_associations
    ADD CONSTRAINT instrument_log_entry_version_category_associa_log_entry_id_fkey FOREIGN KEY (log_entry_id, log_entry_version_id) REFERENCES public.instrument_log_entry_versions(log_entry_id, version_id);


--
-- Name: instrument_log_entry_version_category_associations instrument_log_entry_version_category_associat_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_entry_version_category_associations
    ADD CONSTRAINT instrument_log_entry_version_category_associat_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.instrument_log_categories(id) ON DELETE CASCADE;


--
-- Name: instrument_log_entry_versions instrument_log_entry_versions_log_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_entry_versions
    ADD CONSTRAINT instrument_log_entry_versions_log_entry_id_fkey FOREIGN KEY (log_entry_id) REFERENCES public.instrument_log_entries(id);


--
-- Name: instrument_log_file_attachments instrument_log_file_attachments_log_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_file_attachments
    ADD CONSTRAINT instrument_log_file_attachments_log_entry_id_fkey FOREIGN KEY (log_entry_id) REFERENCES public.instrument_log_entries(id);


--
-- Name: instrument_log_object_attachments instrument_log_object_attachments_log_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_object_attachments
    ADD CONSTRAINT instrument_log_object_attachments_log_entry_id_fkey FOREIGN KEY (log_entry_id) REFERENCES public.instrument_log_entries(id);


--
-- Name: instrument_log_object_attachments instrument_log_object_attachments_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_log_object_attachments
    ADD CONSTRAINT instrument_log_object_attachments_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: instrument_translations instrument_translations_instrument_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_translations
    ADD CONSTRAINT instrument_translations_instrument_id_fkey FOREIGN KEY (instrument_id) REFERENCES public.instruments(id);


--
-- Name: instrument_translations instrument_translations_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrument_translations
    ADD CONSTRAINT instrument_translations_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id);


--
-- Name: locations locations_parent_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_parent_location_id_fkey FOREIGN KEY (parent_location_id) REFERENCES public.locations(id);


--
-- Name: markdown_images markdown_images_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.markdown_images
    ADD CONSTRAINT markdown_images_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notification_mode_for_types notification_mode_for_types_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_mode_for_types
    ADD CONSTRAINT notification_mode_for_types_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: object_location_assignments object_location_assignments_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_location_assignments
    ADD CONSTRAINT object_location_assignments_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id);


--
-- Name: object_location_assignments object_location_assignments_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_location_assignments
    ADD CONSTRAINT object_location_assignments_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: object_location_assignments object_location_assignments_responsible_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_location_assignments
    ADD CONSTRAINT object_location_assignments_responsible_user_id_fkey FOREIGN KEY (responsible_user_id) REFERENCES public.users(id);


--
-- Name: object_location_assignments object_location_assignments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_location_assignments
    ADD CONSTRAINT object_location_assignments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: object_log_entries object_log_entries_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_log_entries
    ADD CONSTRAINT object_log_entries_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: object_log_entries object_log_entries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_log_entries
    ADD CONSTRAINT object_log_entries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: object_publications object_publications_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.object_publications
    ADD CONSTRAINT object_publications_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: objects_current objects_current_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.objects_current
    ADD CONSTRAINT objects_current_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id);


--
-- Name: objects_current objects_current_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.objects_current
    ADD CONSTRAINT objects_current_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: objects_previous objects_previous_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.objects_previous
    ADD CONSTRAINT objects_previous_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id);


--
-- Name: objects_previous objects_previous_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.objects_previous
    ADD CONSTRAINT objects_previous_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: project_action_permissions project_action_permissions_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_action_permissions
    ADD CONSTRAINT project_action_permissions_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id);


--
-- Name: project_action_permissions project_action_permissions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_action_permissions
    ADD CONSTRAINT project_action_permissions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_invitations project_invitations_inviter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_inviter_id_fkey FOREIGN KEY (inviter_id) REFERENCES public.users(id);


--
-- Name: project_invitations project_invitations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_invitations project_invitations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: project_object_association project_object_association_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_object_association
    ADD CONSTRAINT project_object_association_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id) ON DELETE CASCADE;


--
-- Name: project_object_association project_object_association_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_object_association
    ADD CONSTRAINT project_object_association_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_object_permissions project_object_permissions_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_object_permissions
    ADD CONSTRAINT project_object_permissions_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: project_object_permissions project_object_permissions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_object_permissions
    ADD CONSTRAINT project_object_permissions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: public_actions public_actions_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.public_actions
    ADD CONSTRAINT public_actions_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id);


--
-- Name: public_objects public_objects_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.public_objects
    ADD CONSTRAINT public_objects_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: settings settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: subproject_relationship subproject_relationship_child_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subproject_relationship
    ADD CONSTRAINT subproject_relationship_child_project_id_fkey FOREIGN KEY (child_project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: subproject_relationship subproject_relationship_parent_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subproject_relationship
    ADD CONSTRAINT subproject_relationship_parent_project_id_fkey FOREIGN KEY (parent_project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: user_action_permissions user_action_permissions_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_action_permissions
    ADD CONSTRAINT user_action_permissions_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id);


--
-- Name: user_action_permissions user_action_permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_action_permissions
    ADD CONSTRAINT user_action_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_group_memberships user_group_memberships_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_group_memberships
    ADD CONSTRAINT user_group_memberships_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);


--
-- Name: user_group_memberships user_group_memberships_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_group_memberships
    ADD CONSTRAINT user_group_memberships_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_invitations user_invitations_inviter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_invitations
    ADD CONSTRAINT user_invitations_inviter_id_fkey FOREIGN KEY (inviter_id) REFERENCES public.users(id);


--
-- Name: user_log_entries user_log_entries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_log_entries
    ADD CONSTRAINT user_log_entries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_object_permissions user_object_permissions_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_object_permissions
    ADD CONSTRAINT user_object_permissions_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects_current(object_id);


--
-- Name: user_object_permissions user_object_permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_object_permissions
    ADD CONSTRAINT user_object_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_project_permissions user_project_permissions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_project_permissions
    ADD CONSTRAINT user_project_permissions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: user_project_permissions user_project_permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_project_permissions
    ADD CONSTRAINT user_project_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

