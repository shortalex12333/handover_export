-- ============================================================================
-- MIGRATION: 00005_tenant_db_handover.sql
-- PURPOSE: Create complete handover system tables
-- TARGET: Tenant Database
-- UX Source: # 10_supabase_schema.md
-- ============================================================================

-- ============================================================================
-- ENUMS: Handover system enums
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE handover_draft_state AS ENUM ('DRAFT', 'IN_REVIEW', 'ACCEPTED', 'SIGNED', 'EXPORTED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE handover_entry_status AS ENUM ('candidate', 'included', 'suppressed', 'resolved');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE presentation_bucket AS ENUM (
        'Command', 'Engineering', 'ETO_AVIT', 'Deck', 'Interior', 'Galley', 'Security', 'Admin_Compliance'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE risk_tag AS ENUM (
        'Safety_Critical', 'Compliance_Critical', 'Guest_Impacting',
        'Cost_Impacting', 'Operational_Debt', 'Informational'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE confidence_level AS ENUM ('LOW', 'MEDIUM', 'HIGH');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;


-- ============================================================================
-- TABLE: handover_entries (TENANT DB)
-- Purpose: Raw handover entries captured at operational moment
-- These are TRUTH SEEDS - never overwritten or summarized
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,
    -- Tenant isolation

    -- Authorship
    created_by_user_id UUID NOT NULL,
    created_by_role TEXT,
    created_by_department TEXT,

    -- Domain classification
    primary_domain TEXT NOT NULL,
    -- e.g., 'DECK-01', 'ENG-03', 'INT-02'

    secondary_domains TEXT[],
    -- Optional additional domains

    presentation_bucket TEXT NOT NULL,
    -- Which handover section: Command, Engineering, Deck, Interior, etc.

    -- Ownership inference
    suggested_owner_roles TEXT[],
    -- Roles that should see this entry

    -- Risk classification
    risk_tags TEXT[],
    -- Safety_Critical, Compliance_Critical, Guest_Impacting, etc.

    -- Content
    narrative_text TEXT NOT NULL,
    -- User-authored or edited text - THE TRUTH

    summary_text TEXT,
    -- Optional AI-generated summary

    -- Source references (immutable)
    source_event_ids UUID[],
    -- Links to ledger_events

    source_document_ids UUID[],
    -- Links to emails, files, etc.

    source_entity_type TEXT,
    source_entity_id UUID,
    -- Direct entity reference (work_order, fault, etc.)

    -- Status
    status TEXT NOT NULL DEFAULT 'candidate',
    -- candidate / included / suppressed / resolved

    -- Flags
    classification_flagged BOOLEAN DEFAULT FALSE,
    -- User flagged taxonomy error

    is_critical BOOLEAN DEFAULT FALSE,
    -- Marked as critical by user

    requires_acknowledgment BOOLEAN DEFAULT FALSE,
    -- Incoming person must acknowledge

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    CONSTRAINT valid_status CHECK (status IN ('candidate', 'included', 'suppressed', 'resolved')),
    CONSTRAINT valid_bucket CHECK (presentation_bucket IN (
        'Command', 'Engineering', 'ETO_AVIT', 'Deck', 'Interior', 'Galley', 'Security', 'Admin_Compliance'
    ))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_handover_entries_yacht ON public.handover_entries(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_entries_user ON public.handover_entries(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_handover_entries_status ON public.handover_entries(status);
CREATE INDEX IF NOT EXISTS idx_handover_entries_bucket ON public.handover_entries(presentation_bucket);
CREATE INDEX IF NOT EXISTS idx_handover_entries_created ON public.handover_entries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_handover_entries_domain ON public.handover_entries(primary_domain);
CREATE INDEX IF NOT EXISTS idx_handover_entries_source ON public.handover_entries(source_entity_type, source_entity_id);
CREATE INDEX IF NOT EXISTS idx_handover_entries_critical ON public.handover_entries(is_critical) WHERE is_critical = TRUE;


-- ============================================================================
-- TABLE: handover_drafts (TENANT DB)
-- Purpose: Assembled draft handover documents
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,

    -- Period covered
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,

    -- Title and context
    title TEXT,
    -- e.g., "Engineering Handover - 2026-01-14"

    department TEXT,
    -- Primary department for this handover

    -- Generation info
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generated_by_user_id UUID,
    generated_by_version TEXT DEFAULT '1.0',
    generation_method TEXT DEFAULT 'manual',
    -- 'manual', 'scheduled', 'ai_assisted'

    -- State machine
    state TEXT NOT NULL DEFAULT 'DRAFT',
    -- DRAFT -> IN_REVIEW -> ACCEPTED -> SIGNED -> EXPORTED

    -- Modification tracking
    last_modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_modified_by UUID,

    -- Entry counts
    total_entries INTEGER DEFAULT 0,
    critical_entries INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_state CHECK (state IN ('DRAFT', 'IN_REVIEW', 'ACCEPTED', 'SIGNED', 'EXPORTED'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_handover_drafts_yacht ON public.handover_drafts(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_drafts_state ON public.handover_drafts(state);
CREATE INDEX IF NOT EXISTS idx_handover_drafts_period ON public.handover_drafts(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_handover_drafts_department ON public.handover_drafts(department);


-- ============================================================================
-- TABLE: handover_draft_sections (TENANT DB)
-- Purpose: Visible document structure within a draft
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_draft_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    draft_id UUID NOT NULL REFERENCES public.handover_drafts(id) ON DELETE CASCADE,

    -- Section info
    bucket_name TEXT NOT NULL,
    -- Command, Engineering, ETO_AVIT, Deck, Interior, Admin_Compliance

    section_order INTEGER NOT NULL,
    -- Display order

    -- Section title (can override bucket_name)
    display_title TEXT,

    -- Counts
    item_count INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(draft_id, bucket_name)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_handover_draft_sections_draft ON public.handover_draft_sections(draft_id);


-- ============================================================================
-- TABLE: handover_draft_items (TENANT DB)
-- Purpose: Summarized narrative entries inside a draft
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_draft_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    draft_id UUID NOT NULL REFERENCES public.handover_drafts(id) ON DELETE CASCADE,
    section_id UUID REFERENCES public.handover_draft_sections(id) ON DELETE SET NULL,

    -- Classification
    section_bucket TEXT NOT NULL,
    domain_code TEXT,

    -- Content
    summary_text TEXT NOT NULL,
    -- The actual handover text

    -- Source references
    source_entry_ids UUID[],
    -- References to handover_entries

    source_event_ids UUID[],
    -- References to ledger

    -- Risk and confidence
    risk_tags TEXT[],
    confidence_level TEXT DEFAULT 'HIGH',

    -- Ordering
    item_order INTEGER NOT NULL,

    -- Flags
    conflict_flag BOOLEAN DEFAULT FALSE,
    -- Conflicting information detected

    uncertainty_flag BOOLEAN DEFAULT FALSE,
    -- AI indicated uncertainty

    is_critical BOOLEAN DEFAULT FALSE,

    requires_action BOOLEAN DEFAULT FALSE,
    action_summary TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_confidence CHECK (confidence_level IN ('LOW', 'MEDIUM', 'HIGH'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_handover_draft_items_draft ON public.handover_draft_items(draft_id);
CREATE INDEX IF NOT EXISTS idx_handover_draft_items_section ON public.handover_draft_items(section_id);
CREATE INDEX IF NOT EXISTS idx_handover_draft_items_bucket ON public.handover_draft_items(section_bucket);
CREATE INDEX IF NOT EXISTS idx_handover_draft_items_critical ON public.handover_draft_items(is_critical) WHERE is_critical = TRUE;


-- ============================================================================
-- TABLE: handover_draft_edits (TENANT DB)
-- Purpose: Audit trail of human edits to draft items
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_draft_edits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    draft_id UUID NOT NULL REFERENCES public.handover_drafts(id) ON DELETE CASCADE,
    draft_item_id UUID REFERENCES public.handover_draft_items(id) ON DELETE SET NULL,

    -- Edit details
    edited_by_user_id UUID NOT NULL,
    edited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Change tracking
    field_edited TEXT NOT NULL DEFAULT 'summary_text',
    original_text TEXT,
    edited_text TEXT NOT NULL,
    edit_reason TEXT,

    -- Edit type
    edit_type TEXT DEFAULT 'modification',
    -- 'modification', 'addition', 'removal', 'reorder'

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_handover_draft_edits_draft ON public.handover_draft_edits(draft_id);
CREATE INDEX IF NOT EXISTS idx_handover_draft_edits_item ON public.handover_draft_edits(draft_item_id);
CREATE INDEX IF NOT EXISTS idx_handover_draft_edits_user ON public.handover_draft_edits(edited_by_user_id);


-- ============================================================================
-- TABLE: handover_signoffs (TENANT DB)
-- Purpose: Stores acceptance and countersignature
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_signoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    draft_id UUID NOT NULL REFERENCES public.handover_drafts(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL,

    -- Outgoing person (handing over)
    outgoing_user_id UUID NOT NULL,
    outgoing_role TEXT,
    outgoing_signed_at TIMESTAMPTZ,
    outgoing_notes TEXT,

    -- Incoming person (receiving)
    incoming_user_id UUID,
    incoming_role TEXT,
    incoming_signed_at TIMESTAMPTZ,
    incoming_notes TEXT,
    incoming_acknowledged_critical BOOLEAN DEFAULT FALSE,

    -- Document integrity
    document_hash TEXT,
    -- SHA256 hash of the draft at sign time

    -- Status
    signoff_complete BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(draft_id)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_handover_signoffs_draft ON public.handover_signoffs(draft_id);
CREATE INDEX IF NOT EXISTS idx_handover_signoffs_yacht ON public.handover_signoffs(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_signoffs_outgoing ON public.handover_signoffs(outgoing_user_id);
CREATE INDEX IF NOT EXISTS idx_handover_signoffs_incoming ON public.handover_signoffs(incoming_user_id);


-- ============================================================================
-- TABLE: handover_exports (TENANT DB)
-- Purpose: Track exported artifacts (PDF, HTML, Email)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    draft_id UUID NOT NULL REFERENCES public.handover_drafts(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL,

    -- Export type
    export_type TEXT NOT NULL,
    -- 'pdf', 'html', 'email'

    -- Storage
    storage_path TEXT,
    storage_bucket TEXT DEFAULT 'handover-exports',
    file_name TEXT,
    file_size_bytes INTEGER,

    -- Export details
    exported_by_user_id UUID NOT NULL,
    exported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Email specific
    recipients TEXT[],
    email_subject TEXT,
    email_sent_at TIMESTAMPTZ,

    -- Integrity
    document_hash TEXT,

    -- Status
    export_status TEXT DEFAULT 'completed',
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_export_type CHECK (export_type IN ('pdf', 'html', 'email'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_handover_exports_draft ON public.handover_exports(draft_id);
CREATE INDEX IF NOT EXISTS idx_handover_exports_yacht ON public.handover_exports(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_exports_user ON public.handover_exports(exported_by_user_id);
CREATE INDEX IF NOT EXISTS idx_handover_exports_type ON public.handover_exports(export_type);


-- ============================================================================
-- TABLE: handover_sources (TENANT DB)
-- Purpose: Map external source material (emails, documents)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,

    -- Source identification
    source_type TEXT NOT NULL,
    -- 'email', 'document', 'work_order', 'fault', 'message', 'api'

    external_id TEXT,
    -- ID in external system (e.g., Microsoft Graph message ID)

    -- Storage
    storage_path TEXT,
    storage_bucket TEXT,

    -- Content cache
    subject TEXT,
    body_preview TEXT,
    sender_name TEXT,
    sender_email TEXT,
    received_at TIMESTAMPTZ,

    -- Processing status
    is_processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    processing_error TEXT,

    -- Classification results (from AI)
    classification JSONB,
    -- {category, summary, confidence}

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_source_type CHECK (source_type IN ('email', 'document', 'work_order', 'fault', 'message', 'api'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_handover_sources_yacht ON public.handover_sources(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_sources_type ON public.handover_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_handover_sources_external ON public.handover_sources(external_id);
CREATE INDEX IF NOT EXISTS idx_handover_sources_processed ON public.handover_sources(is_processed);


-- ============================================================================
-- TABLE: email_extraction_jobs (TENANT DB)
-- Purpose: Track email extraction pipeline jobs
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.email_extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,

    -- Job configuration
    query TEXT,
    -- Search query for emails

    days_back INTEGER DEFAULT 90,
    max_emails INTEGER DEFAULT 500,
    folder_id TEXT,

    -- Job status
    status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'running', 'completed', 'failed'

    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Results
    emails_fetched INTEGER DEFAULT 0,
    emails_classified INTEGER DEFAULT 0,
    entries_created INTEGER DEFAULT 0,

    -- Pipeline progress
    current_stage TEXT,
    stage_progress JSONB DEFAULT '{}',

    -- Error tracking
    error_message TEXT,
    error_details JSONB,

    -- Output
    draft_id UUID,
    -- Created draft if generation was requested

    -- Metadata
    created_by_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_job_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_extraction_jobs_yacht ON public.email_extraction_jobs(yacht_id);
CREATE INDEX IF NOT EXISTS idx_email_extraction_jobs_status ON public.email_extraction_jobs(status);
CREATE INDEX IF NOT EXISTS idx_email_extraction_jobs_user ON public.email_extraction_jobs(created_by_user_id);


-- ============================================================================
-- RLS POLICIES: Handover tables
-- ============================================================================

ALTER TABLE public.handover_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_draft_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_draft_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_draft_edits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_signoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_extraction_jobs ENABLE ROW LEVEL SECURITY;

-- Handover entries: Yacht members can read, create, update (not delete)
CREATE POLICY "handover_entries_read" ON public.handover_entries
    FOR SELECT TO authenticated
    USING (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

CREATE POLICY "handover_entries_insert" ON public.handover_entries
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

CREATE POLICY "handover_entries_update" ON public.handover_entries
    FOR UPDATE TO authenticated
    USING (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()))
    WITH CHECK (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

-- NO DELETE on handover_entries - they are immutable truth seeds

-- Handover drafts: Yacht members can read and manage
CREATE POLICY "handover_drafts_read" ON public.handover_drafts
    FOR SELECT TO authenticated
    USING (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

CREATE POLICY "handover_drafts_insert" ON public.handover_drafts
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

CREATE POLICY "handover_drafts_update" ON public.handover_drafts
    FOR UPDATE TO authenticated
    USING (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

-- No delete on SIGNED drafts (enforced in RPC)
CREATE POLICY "handover_drafts_delete" ON public.handover_drafts
    FOR DELETE TO authenticated
    USING (
        yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid())
        AND state IN ('DRAFT', 'IN_REVIEW')
    );

-- Draft sections, items, edits: Cascade from drafts
CREATE POLICY "draft_sections_all" ON public.handover_draft_sections
    FOR ALL TO authenticated
    USING (draft_id IN (SELECT id FROM public.handover_drafts WHERE yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid())));

CREATE POLICY "draft_items_all" ON public.handover_draft_items
    FOR ALL TO authenticated
    USING (draft_id IN (SELECT id FROM public.handover_drafts WHERE yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid())));

CREATE POLICY "draft_edits_all" ON public.handover_draft_edits
    FOR ALL TO authenticated
    USING (draft_id IN (SELECT id FROM public.handover_drafts WHERE yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid())));

-- Signoffs: Yacht members can read and manage
CREATE POLICY "signoffs_all" ON public.handover_signoffs
    FOR ALL TO authenticated
    USING (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

-- Exports: Yacht members can read and create
CREATE POLICY "exports_read" ON public.handover_exports
    FOR SELECT TO authenticated
    USING (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

CREATE POLICY "exports_insert" ON public.handover_exports
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

-- Sources and jobs: Yacht members
CREATE POLICY "sources_all" ON public.handover_sources
    FOR ALL TO authenticated
    USING (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

CREATE POLICY "jobs_all" ON public.email_extraction_jobs
    FOR ALL TO authenticated
    USING (yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

-- Service role full access
CREATE POLICY "handover_entries_service" ON public.handover_entries FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "handover_drafts_service" ON public.handover_drafts FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "draft_sections_service" ON public.handover_draft_sections FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "draft_items_service" ON public.handover_draft_items FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "draft_edits_service" ON public.handover_draft_edits FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "signoffs_service" ON public.handover_signoffs FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "exports_service" ON public.handover_exports FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "sources_service" ON public.handover_sources FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "jobs_service" ON public.email_extraction_jobs FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);


-- ============================================================================
-- RPC FUNCTIONS: Handover operations
-- ============================================================================

-- Create handover entry
CREATE OR REPLACE FUNCTION public.create_handover_entry(
    p_narrative_text TEXT,
    p_primary_domain TEXT,
    p_presentation_bucket TEXT,
    p_source_entity_type TEXT DEFAULT NULL,
    p_source_entity_id UUID DEFAULT NULL,
    p_risk_tags TEXT[] DEFAULT '{}',
    p_is_critical BOOLEAN DEFAULT FALSE
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
    v_user_role TEXT;
    v_user_dept TEXT;
    v_entry_id UUID;
BEGIN
    v_user_id := auth.uid();
    SELECT yacht_id INTO v_yacht_id FROM auth_users_profiles WHERE id = v_user_id;
    SELECT role, department INTO v_user_role, v_user_dept FROM auth_users_roles WHERE user_id = v_user_id AND is_active = TRUE LIMIT 1;

    INSERT INTO handover_entries (
        yacht_id, created_by_user_id, created_by_role, created_by_department,
        primary_domain, presentation_bucket, narrative_text,
        source_entity_type, source_entity_id, risk_tags, is_critical
    )
    VALUES (
        v_yacht_id, v_user_id, v_user_role, v_user_dept,
        p_primary_domain, p_presentation_bucket, p_narrative_text,
        p_source_entity_type, p_source_entity_id, p_risk_tags, p_is_critical
    )
    RETURNING id INTO v_entry_id;

    -- Record to ledger
    PERFORM record_ledger_event(
        'handover_entry', v_entry_id, 'create', 'handover_entry_created',
        NULL,
        jsonb_build_object('narrative', p_narrative_text, 'domain', p_primary_domain),
        'Handover entry created: ' || LEFT(p_narrative_text, 50),
        'handover'
    );

    RETURN v_entry_id;
END;
$$;

-- Create handover draft
CREATE OR REPLACE FUNCTION public.create_handover_draft(
    p_period_start TIMESTAMPTZ,
    p_period_end TIMESTAMPTZ,
    p_department TEXT DEFAULT NULL,
    p_title TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
    v_draft_id UUID;
    v_title TEXT;
BEGIN
    v_user_id := auth.uid();
    SELECT yacht_id INTO v_yacht_id FROM auth_users_profiles WHERE id = v_user_id;

    v_title := COALESCE(p_title, COALESCE(p_department, 'General') || ' Handover - ' || TO_CHAR(p_period_end, 'YYYY-MM-DD'));

    INSERT INTO handover_drafts (
        yacht_id, period_start, period_end, title, department, generated_by_user_id
    )
    VALUES (
        v_yacht_id, p_period_start, p_period_end, v_title, p_department, v_user_id
    )
    RETURNING id INTO v_draft_id;

    RETURN v_draft_id;
END;
$$;

-- Sign handover (outgoing)
CREATE OR REPLACE FUNCTION public.sign_handover_outgoing(
    p_draft_id UUID,
    p_notes TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
    v_user_role TEXT;
    v_draft_state TEXT;
    v_signoff_id UUID;
    v_doc_hash TEXT;
BEGIN
    v_user_id := auth.uid();
    SELECT yacht_id INTO v_yacht_id FROM auth_users_profiles WHERE id = v_user_id;
    SELECT role INTO v_user_role FROM auth_users_roles WHERE user_id = v_user_id AND is_active = TRUE LIMIT 1;

    -- Check draft state
    SELECT state INTO v_draft_state FROM handover_drafts WHERE id = p_draft_id AND yacht_id = v_yacht_id;

    IF v_draft_state IS NULL THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Draft not found');
    END IF;

    IF v_draft_state NOT IN ('DRAFT', 'IN_REVIEW', 'ACCEPTED') THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Draft already signed or exported');
    END IF;

    -- Generate document hash
    SELECT encode(sha256(
        (SELECT string_agg(summary_text, '|' ORDER BY item_order)
         FROM handover_draft_items WHERE draft_id = p_draft_id)::bytea
    ), 'hex') INTO v_doc_hash;

    -- Create or update signoff
    INSERT INTO handover_signoffs (
        draft_id, yacht_id, outgoing_user_id, outgoing_role, outgoing_signed_at, outgoing_notes, document_hash
    )
    VALUES (
        p_draft_id, v_yacht_id, v_user_id, v_user_role, NOW(), p_notes, v_doc_hash
    )
    ON CONFLICT (draft_id) DO UPDATE SET
        outgoing_user_id = v_user_id,
        outgoing_role = v_user_role,
        outgoing_signed_at = NOW(),
        outgoing_notes = p_notes,
        document_hash = v_doc_hash,
        updated_at = NOW()
    RETURNING id INTO v_signoff_id;

    -- Update draft state
    UPDATE handover_drafts
    SET state = 'ACCEPTED', last_modified_at = NOW(), last_modified_by = v_user_id
    WHERE id = p_draft_id;

    RETURN jsonb_build_object(
        'success', TRUE,
        'signoff_id', v_signoff_id,
        'document_hash', v_doc_hash,
        'signed_at', NOW()
    );
END;
$$;

-- Sign handover (incoming / countersign)
CREATE OR REPLACE FUNCTION public.sign_handover_incoming(
    p_draft_id UUID,
    p_notes TEXT DEFAULT NULL,
    p_acknowledge_critical BOOLEAN DEFAULT FALSE
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
    v_user_role TEXT;
    v_draft_state TEXT;
    v_signoff RECORD;
    v_has_critical BOOLEAN;
BEGIN
    v_user_id := auth.uid();
    SELECT yacht_id INTO v_yacht_id FROM auth_users_profiles WHERE id = v_user_id;
    SELECT role INTO v_user_role FROM auth_users_roles WHERE user_id = v_user_id AND is_active = TRUE LIMIT 1;

    -- Check draft state
    SELECT state INTO v_draft_state FROM handover_drafts WHERE id = p_draft_id AND yacht_id = v_yacht_id;

    IF v_draft_state IS NULL THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Draft not found');
    END IF;

    IF v_draft_state != 'ACCEPTED' THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Draft must be signed by outgoing person first');
    END IF;

    -- Check for critical items
    SELECT EXISTS(SELECT 1 FROM handover_draft_items WHERE draft_id = p_draft_id AND is_critical = TRUE) INTO v_has_critical;

    IF v_has_critical AND NOT p_acknowledge_critical THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Must acknowledge critical items', 'has_critical', TRUE);
    END IF;

    -- Get existing signoff
    SELECT * INTO v_signoff FROM handover_signoffs WHERE draft_id = p_draft_id;

    IF v_signoff IS NULL THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'No outgoing signature found');
    END IF;

    -- Update signoff with incoming
    UPDATE handover_signoffs
    SET
        incoming_user_id = v_user_id,
        incoming_role = v_user_role,
        incoming_signed_at = NOW(),
        incoming_notes = p_notes,
        incoming_acknowledged_critical = p_acknowledge_critical,
        signoff_complete = TRUE,
        updated_at = NOW()
    WHERE id = v_signoff.id;

    -- Update draft state to SIGNED
    UPDATE handover_drafts
    SET state = 'SIGNED', last_modified_at = NOW(), last_modified_by = v_user_id
    WHERE id = p_draft_id;

    -- Record to ledger
    PERFORM record_ledger_event(
        'handover_draft', p_draft_id, 'status_change', 'handover_signed',
        jsonb_build_object('state', 'ACCEPTED'),
        jsonb_build_object('state', 'SIGNED', 'incoming_user', v_user_id),
        'Handover signed and accepted',
        'handover'
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'signed_at', NOW(),
        'state', 'SIGNED'
    );
END;
$$;

-- Get handover entries for period
CREATE OR REPLACE FUNCTION public.get_handover_entries_for_period(
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ,
    p_department TEXT DEFAULT NULL,
    p_include_resolved BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    id UUID,
    primary_domain TEXT,
    presentation_bucket TEXT,
    narrative_text TEXT,
    risk_tags TEXT[],
    is_critical BOOLEAN,
    status TEXT,
    created_by_role TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_yacht_id UUID;
BEGIN
    SELECT yacht_id INTO v_yacht_id FROM auth_users_profiles WHERE id = auth.uid();

    RETURN QUERY
    SELECT
        e.id,
        e.primary_domain,
        e.presentation_bucket,
        e.narrative_text,
        e.risk_tags,
        e.is_critical,
        e.status,
        e.created_by_role,
        e.created_at
    FROM handover_entries e
    WHERE e.yacht_id = v_yacht_id
    AND e.created_at >= p_start_date
    AND e.created_at <= p_end_date
    AND (p_department IS NULL OR e.created_by_department = p_department)
    AND (p_include_resolved OR e.status != 'resolved')
    ORDER BY e.is_critical DESC, e.created_at DESC;
END;
$$;

GRANT EXECUTE ON FUNCTION public.create_handover_entry TO authenticated;
GRANT EXECUTE ON FUNCTION public.create_handover_draft TO authenticated;
GRANT EXECUTE ON FUNCTION public.sign_handover_outgoing TO authenticated;
GRANT EXECUTE ON FUNCTION public.sign_handover_incoming TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_handover_entries_for_period TO authenticated;
