--- Database schema for print2here_health
--- Schema developed on PostgreSQL 9.1

---
--- TABLES
---

CREATE TABLE pagecounts (
    day date NOT NULL,
    name character varying(15) NOT NULL,
    count integer NOT NULL,
    
    PRIMARY KEY (day, name)
);

CREATE TABLE periods (
    start timestamp without time zone NOT NULL,
    "end" timestamp without time zone NOT NULL,
    name character varying(15) NOT NULL,
    status character(1) NOT NULL,
    start_count integer NOT NULL,
    end_count integer NOT NULL,
    groupid integer NOT NULL,

    PRIMARY KEY (start, name)
);

CREATE TABLE status (
    "timestamp" timestamp without time zone NOT NULL,
    name character varying(15) NOT NULL,
    status character(1) NOT NULL,
    count integer,

    PRIMARY KEY ("timestamp", name)
);

CREATE TABLE subscription (
    name character varying(15),
    number character(12),

    PRIMARY KEY (name, number)
);

---
--- VIEWS
---

CREATE VIEW PeriodsSummary AS
        SELECT start, ("end" - start) AS duration, name, status, (end_count - start_count) AS delta_count
        FROM Periods
        ORDER BY start;

---
--- INDEXES
---

CREATE INDEX periods_name_status_idx ON periods (name, status);

---
--- FUNCTIONS
---

CREATE OR REPLACE FUNCTION update_periods() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    last_group_number INTEGER;
    last_status character(1);
BEGIN
    SELECT groupid, status INTO last_group_number, last_status FROM Periods WHERE name=NEW.name ORDER BY start DESC LIMIT 1;

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

CREATE OR REPLACE FUNCTION update_counts() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    day_start_count integer;
BEGIN
    SELECT MIN(count) INTO day_start_count FROM status WHERE name=NEW.name AND timestamp::date = NEW.timestamp::date AND count > 0;
    IF NEW.count > 0 AND day_start_count IS NOT NULL THEN
        UPDATE pagecounts SET count = NEW.count - day_start_count WHERE day = NEW.timestamp::date AND name = NEW.name;
        INSERT INTO pagecounts (day, name, count) SELECT NEW.timestamp::date, NEW.name, NEW.count - day_start_count WHERE 1 NOT IN (SELECT 1 FROM pagecounts WHERE day = NEW.timestamp::date AND name = NEW.name);
        RETURN NEW;
    END IF;    
    RETURN NEW;
END;
$$;

---
--- TRIGGERS
---

CREATE TRIGGER new_status AFTER INSERT ON status FOR EACH ROW EXECUTE PROCEDURE handle_status_update();
CREATE TRIGGER pagecount_update AFTER INSERT ON status FOR EACH ROW EXECUTE PROCEDURE update_counts();
