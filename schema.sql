--- Database schema for print2here_health
--- Schema developed on PostgreSQL 9.1

CREATE TABLE outage (
    id serial NOT NULL,
    name character varying(15) NOT NULL,
    start timestamp without time zone NOT NULL,
    "end" timestamp without time zone,
    description character(1)
);

CREATE TABLE status (
    id serial NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    name character varying(15) NOT NULL,
    status character(1) NOT NULL,
    count integer
);

CREATE TABLE subscription (
    id serial NOT NULL,
    name character varying(15),
    number character(12)
);

ALTER TABLE ONLY outage
    ADD CONSTRAINT outage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY status
    ADD CONSTRAINT status_pkey PRIMARY KEY (id);

ALTER TABLE ONLY subscription
    ADD CONSTRAINT subscription_pkey PRIMARY KEY (id);
