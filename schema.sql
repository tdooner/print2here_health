--- Database schema for print2here_health
--- Schema developed on PostgreSQL 9.1

---
--- TABLES
---

CREATE TABLE outage (
    id serial NOT NULL,
    name character varying(15) NOT NULL,
    start timestamp without time zone NOT NULL,
    "end" timestamp without time zone,
    description character(1)
);

CREATE TABLE periods (
    id serial NOT NULL,
    start timestamp without time zone NOT NULL,
    "end" timestamp without time zone NOT NULL,
    name character varying(15) NOT NULL,
    status character(1) NOT NULL,
    start_count integer NOT NULL,
    end_count integer NOT NULL,
    groupid integer NOT NULL
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

---
--- VIEWS
---

CREATE VIEW PeriodsSummary AS
        SELECT start, ("end" - start) AS duration, name, status, (end_count - start_count) AS delta_count
        FROM Periods
        ORDER BY start;

---
--- FUNCTIONS
---

CREATE FUNCTION handle_status_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    last_group_number INTEGER;
    last_status character(1);
BEGIN
    SELECT groupid, status INTO last_group_number, last_status FROM Periods WHERE name=NEW.name ORDER BY id DESC LIMIT 1;

    IF NOT FOUND THEN
        INSERT INTO Periods ("start", "end", start_count, end_count, name, status, groupid) VALUES (NEW.timestamp, NEW.timestamp, NEW.count, NEW.count, NEW.name, NEW.status, 0);
        RETURN NEW;
    END IF;

    UPDATE Periods SET "end" = NEW.timestamp, end_count = NEW.count WHERE name=NEW.name AND groupid=last_group_number;

    IF last_status <> NEW.status THEN
        INSERT INTO Periods ("start", "end", start_count, end_count, name, status, groupid) VALUES (NEW.timestamp, NEW.timestamp, NEW.count, NEW.count, NEW.name, NEW.status, last_group_number + 1);
        RETURN NEW;
    END IF;

    RETURN NEW;
END;
$$;

---
--- TRIGGERS
---

CREATE TRIGGER new_status AFTER INSERT ON status FOR EACH ROW EXECUTE PROCEDURE handle_status_update();
