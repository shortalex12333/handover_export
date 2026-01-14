-- ============================================================================
-- MIGRATION: 00001_master_db_roles.sql
-- PURPOSE: Create role_definitions and department_definitions tables
-- TARGET: Master Database
-- ============================================================================

-- ============================================================================
-- TABLE: role_definitions (MASTER DB)
-- Purpose: System-wide role definitions for all yacht positions
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.role_definitions (
    id TEXT PRIMARY KEY,
    -- e.g., 'captain', 'chief_engineer', 'bosun', 'deckhand'

    -- Display information
    display_name TEXT NOT NULL,
    display_name_plural TEXT NOT NULL,
    abbreviation TEXT,
    -- e.g., 'CE' for Chief Engineer, 'ETO' for Electro-Technical Officer

    -- Hierarchy
    department TEXT NOT NULL,
    -- Values: 'command', 'deck', 'engineering', 'interior', 'galley', 'security', 'admin'

    rank_order INTEGER NOT NULL,
    -- Lower = higher authority (Captain = 1)

    reports_to TEXT,
    -- Role ID of direct supervisor (NULL for Captain)

    -- Authority scope
    authority_level TEXT NOT NULL,
    -- Values: 'command', 'department_head', 'senior', 'junior'

    can_view_other_departments BOOLEAN DEFAULT FALSE,
    can_countersign_handover BOOLEAN DEFAULT FALSE,
    can_approve_work_orders BOOLEAN DEFAULT FALSE,
    can_view_audit_log BOOLEAN DEFAULT FALSE,

    -- Search behavior defaults
    default_search_scope TEXT DEFAULT 'own_department',
    -- Values: 'own_department', 'all_departments', 'assigned_only'

    search_result_limit INTEGER DEFAULT 10,

    -- UI preferences
    default_landing_view TEXT DEFAULT 'search',
    show_department_summary BOOLEAN DEFAULT FALSE,

    -- Metadata
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_department CHECK (department IN (
        'command', 'deck', 'engineering', 'interior', 'galley', 'security', 'admin', 'medical'
    )),
    CONSTRAINT valid_authority CHECK (authority_level IN (
        'command', 'department_head', 'senior', 'junior'
    ))
);

-- Index for hierarchy queries
CREATE INDEX IF NOT EXISTS idx_role_definitions_department ON public.role_definitions(department);
CREATE INDEX IF NOT EXISTS idx_role_definitions_reports_to ON public.role_definitions(reports_to);
CREATE INDEX IF NOT EXISTS idx_role_definitions_rank ON public.role_definitions(rank_order);

-- ============================================================================
-- SEED DATA: All 30+ yacht roles from all_ranks.md
-- ============================================================================

INSERT INTO public.role_definitions (
    id, display_name, display_name_plural, abbreviation, department, rank_order,
    reports_to, authority_level, can_view_other_departments, can_countersign_handover,
    can_approve_work_orders, can_view_audit_log, default_search_scope, show_department_summary
) VALUES

-- Command Department
('captain', 'Captain', 'Captains', 'Capt', 'command', 1, NULL, 'command', TRUE, TRUE, TRUE, TRUE, 'all_departments', TRUE),
('staff_captain', 'Staff Captain', 'Staff Captains', 'SC', 'command', 2, 'captain', 'command', TRUE, TRUE, TRUE, TRUE, 'all_departments', TRUE),
('second_officer', 'Second Officer', 'Second Officers', '2/O', 'command', 3, 'staff_captain', 'senior', TRUE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('third_officer', 'Third Officer', 'Third Officers', '3/O', 'command', 4, 'second_officer', 'junior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('safety_officer', 'Safety Officer', 'Safety Officers', 'SO', 'command', 5, 'captain', 'senior', TRUE, FALSE, TRUE, TRUE, 'all_departments', FALSE),

-- Deck Department
('chief_officer', 'Chief Officer', 'Chief Officers', 'C/O', 'deck', 6, 'staff_captain', 'department_head', FALSE, TRUE, TRUE, TRUE, 'own_department', TRUE),
('bosun', 'Bosun', 'Bosuns', 'Bosun', 'deck', 7, 'chief_officer', 'senior', FALSE, TRUE, FALSE, FALSE, 'own_department', FALSE),
('senior_deckhand', 'Senior Deckhand', 'Senior Deckhands', 'Sr DH', 'deck', 8, 'bosun', 'senior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('deckhand', 'Deckhand', 'Deckhands', 'DH', 'deck', 9, 'bosun', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('deckhand_tender', 'Deckhand / Tender Driver', 'Deckhand / Tender Drivers', 'DH/T', 'deck', 10, 'bosun', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('deckhand_watersports', 'Deckhand / Watersports', 'Deckhand / Watersports', 'DH/WS', 'deck', 11, 'bosun', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('junior_deckhand', 'Junior Deckhand', 'Junior Deckhands', 'Jr DH', 'deck', 12, 'bosun', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('deck_cadet', 'Deck Cadet', 'Deck Cadets', 'Cadet', 'deck', 13, 'bosun', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),

-- Engineering Department
('chief_engineer', 'Chief Engineer', 'Chief Engineers', 'CE', 'engineering', 14, 'captain', 'department_head', FALSE, TRUE, TRUE, TRUE, 'own_department', TRUE),
('second_engineer', 'Second Engineer', 'Second Engineers', '2/E', 'engineering', 15, 'chief_engineer', 'senior', FALSE, TRUE, TRUE, FALSE, 'own_department', FALSE),
('third_engineer', 'Third Engineer', 'Third Engineers', '3/E', 'engineering', 16, 'second_engineer', 'senior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('fourth_engineer', 'Fourth Engineer', 'Fourth Engineers', '4/E', 'engineering', 17, 'third_engineer', 'junior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('eto', 'Electro-Technical Officer', 'ETOs', 'ETO', 'engineering', 18, 'chief_engineer', 'senior', FALSE, TRUE, FALSE, FALSE, 'own_department', FALSE),
('avit_officer', 'AV/IT Officer', 'AV/IT Officers', 'AV/IT', 'engineering', 19, 'eto', 'senior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('engineer_watchkeeper', 'Engineer Watchkeeper', 'Engineer Watchkeepers', 'E/W', 'engineering', 20, 'second_engineer', 'junior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('motorman', 'Motorman', 'Motormen', 'MM', 'engineering', 21, 'third_engineer', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('oiler', 'Oiler', 'Oilers', 'Oiler', 'engineering', 22, 'third_engineer', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),

-- Interior Department
('chief_stew', 'Chief Steward/ess', 'Chief Stewards', 'CS', 'interior', 23, 'captain', 'department_head', FALSE, TRUE, TRUE, TRUE, 'own_department', TRUE),
('purser', 'Purser', 'Pursers', 'Purser', 'interior', 24, 'chief_stew', 'senior', FALSE, TRUE, TRUE, TRUE, 'own_department', FALSE),
('deputy_chief_stew', 'Deputy Chief Steward/ess', 'Deputy Chiefs', 'DCS', 'interior', 25, 'chief_stew', 'senior', FALSE, TRUE, FALSE, FALSE, 'own_department', FALSE),
('head_housekeeping', 'Head of Housekeeping', 'Housekeeping Heads', 'HH', 'interior', 26, 'chief_stew', 'senior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('head_service', 'Head of Service', 'Service Heads', 'HS', 'interior', 27, 'chief_stew', 'senior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('steward', 'Steward/ess', 'Stewards', 'Stew', 'interior', 28, 'deputy_chief_stew', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('second_stew', 'Second Steward/ess', 'Second Stewards', '2nd Stew', 'interior', 29, 'deputy_chief_stew', 'junior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('third_stew', 'Third Steward/ess', 'Third Stewards', '3rd Stew', 'interior', 30, 'second_stew', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('junior_stew', 'Junior Steward/ess', 'Junior Stewards', 'Jr Stew', 'interior', 31, 'second_stew', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('laundry_stew', 'Laundry Steward/ess', 'Laundry Stewards', 'Laundry', 'interior', 32, 'head_housekeeping', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('spa_therapist', 'Spa Therapist', 'Spa Therapists', 'Spa', 'interior', 33, 'chief_stew', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('beauty_therapist', 'Beauty Therapist', 'Beauty Therapists', 'Beauty', 'interior', 34, 'chief_stew', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),

-- Galley Department
('executive_chef', 'Executive Chef', 'Executive Chefs', 'Chef', 'galley', 35, 'captain', 'department_head', FALSE, TRUE, TRUE, FALSE, 'own_department', TRUE),
('head_chef', 'Head Chef', 'Head Chefs', 'Head Chef', 'galley', 36, 'executive_chef', 'senior', FALSE, FALSE, TRUE, FALSE, 'own_department', FALSE),
('sous_chef', 'Sous Chef', 'Sous Chefs', 'Sous', 'galley', 37, 'head_chef', 'senior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('chef_de_partie', 'Chef de Partie', 'Chefs de Partie', 'CDP', 'galley', 38, 'sous_chef', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('crew_chef', 'Crew Chef', 'Crew Chefs', 'CC', 'galley', 39, 'sous_chef', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),
('pastry_chef', 'Pastry Chef', 'Pastry Chefs', 'Pastry', 'galley', 40, 'sous_chef', 'senior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),
('commis_chef', 'Commis Chef', 'Commis Chefs', 'Commis', 'galley', 41, 'chef_de_partie', 'junior', FALSE, FALSE, FALSE, FALSE, 'assigned_only', FALSE),

-- Security Department
('head_security', 'Head of Security', 'Security Heads', 'HoS', 'security', 42, 'captain', 'department_head', TRUE, TRUE, FALSE, TRUE, 'all_departments', TRUE),
('security_officer', 'Security Officer', 'Security Officers', 'SecO', 'security', 43, 'head_security', 'junior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),

-- Medical Department
('ships_medic', 'Ship''s Medic', 'Ship''s Medics', 'Medic', 'medical', 44, 'captain', 'senior', TRUE, FALSE, FALSE, FALSE, 'all_departments', FALSE),
('ships_nurse', 'Ship''s Nurse', 'Ship''s Nurses', 'Nurse', 'medical', 45, 'ships_medic', 'junior', FALSE, FALSE, FALSE, FALSE, 'own_department', FALSE),

-- Admin Department (Shore-based or hybrid)
('yacht_manager', 'Yacht Manager', 'Yacht Managers', 'YM', 'admin', 0, NULL, 'command', TRUE, TRUE, TRUE, TRUE, 'all_departments', TRUE),
('fleet_manager', 'Fleet Manager', 'Fleet Managers', 'FM', 'admin', -1, NULL, 'command', TRUE, TRUE, TRUE, TRUE, 'all_departments', TRUE),
('operations_manager', 'Operations Manager', 'Operations Managers', 'OM', 'admin', 1, 'yacht_manager', 'department_head', TRUE, TRUE, TRUE, TRUE, 'all_departments', TRUE)

ON CONFLICT (id) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    display_name_plural = EXCLUDED.display_name_plural,
    abbreviation = EXCLUDED.abbreviation,
    department = EXCLUDED.department,
    rank_order = EXCLUDED.rank_order,
    reports_to = EXCLUDED.reports_to,
    authority_level = EXCLUDED.authority_level,
    can_view_other_departments = EXCLUDED.can_view_other_departments,
    can_countersign_handover = EXCLUDED.can_countersign_handover,
    can_approve_work_orders = EXCLUDED.can_approve_work_orders,
    can_view_audit_log = EXCLUDED.can_view_audit_log;


-- ============================================================================
-- TABLE: department_definitions (MASTER DB)
-- Purpose: Define departments and their domain mappings
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.department_definitions (
    id TEXT PRIMARY KEY,
    -- e.g., 'engineering', 'deck', 'interior'

    display_name TEXT NOT NULL,
    description TEXT,

    -- Domain associations (which data domains this department owns)
    owned_domains TEXT[] NOT NULL,
    -- e.g., ['Equipment', 'Faults', 'Work Orders'] for engineering

    -- Handover configuration
    handover_bucket_template JSONB NOT NULL,
    -- Template for what appears in department handover

    -- UI configuration
    icon TEXT,
    color TEXT,
    display_order INTEGER DEFAULT 100,

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for ordering
CREATE INDEX IF NOT EXISTS idx_department_definitions_order ON public.department_definitions(display_order);

-- ============================================================================
-- SEED DATA: Department definitions with domain mappings
-- ============================================================================

INSERT INTO public.department_definitions (
    id, display_name, description, owned_domains, handover_bucket_template, icon, color, display_order
) VALUES

('command', 'Command',
 'Bridge operations, navigation, and overall vessel management',
 ARRAY['Navigation', 'Compliance', 'Safety', 'Crew', 'Weather', 'Passage Planning'],
 '{
    "sections": ["Bridge Operations", "Regulatory Items", "Crew Status", "Weather & Passage", "Safety Concerns"],
    "critical_domains": ["Safety", "Compliance"],
    "auto_include_severity": "medium"
 }'::jsonb,
 'anchor', '#003366', 1),

('engineering', 'Engineering',
 'Engine room operations, machinery maintenance, and technical systems',
 ARRAY['Equipment', 'Faults', 'Work Orders', 'Technical Documents', 'Machinery', 'HVAC', 'Plumbing', 'Generators'],
 '{
    "sections": ["Engine Room Status", "Active Faults", "Work Orders In Progress", "Pending Parts", "Deferred Maintenance", "Running Hours"],
    "critical_domains": ["Faults", "Equipment"],
    "auto_include_severity": "low"
 }'::jsonb,
 'settings', '#D32F2F', 2),

('deck', 'Deck',
 'Deck operations, tenders, watersports, and exterior maintenance',
 ARRAY['Deck Equipment', 'Tenders', 'Watersports', 'Exterior', 'Anchoring', 'Mooring', 'Paint', 'Varnish'],
 '{
    "sections": ["Deck Status", "Tender Operations", "Exterior Condition", "Scheduled Activities", "Weather Preps"],
    "critical_domains": ["Tenders", "Deck Equipment"],
    "auto_include_severity": "medium"
 }'::jsonb,
 'ship', '#1976D2', 3),

('interior', 'Interior',
 'Guest services, housekeeping, and interior maintenance',
 ARRAY['Inventory', 'Housekeeping', 'Service', 'Guest Preferences', 'Linens', 'Flowers', 'Amenities'],
 '{
    "sections": ["Guest Status", "Service Schedule", "Inventory Alerts", "Housekeeping Status", "Special Requests"],
    "critical_domains": ["Guest Preferences", "Service"],
    "auto_include_severity": "medium"
 }'::jsonb,
 'home', '#7B1FA2', 4),

('galley', 'Galley',
 'Food preparation, provisioning, and dietary management',
 ARRAY['Provisions', 'Menu', 'Dietary', 'Kitchen Equipment', 'Wine', 'Beverages'],
 '{
    "sections": ["Provisioning Status", "Menu Planning", "Dietary Requirements", "Special Events", "Inventory Alerts"],
    "critical_domains": ["Dietary", "Provisions"],
    "auto_include_severity": "medium"
 }'::jsonb,
 'utensils', '#FF5722', 5),

('security', 'Security',
 'Vessel security, access control, and incident management',
 ARRAY['Access Control', 'CCTV', 'Incidents', 'Alarms', 'Safe Haven', 'ISPS'],
 '{
    "sections": ["Security Status", "Incident Reports", "Access Log", "CCTV Notes", "ISPS Compliance"],
    "critical_domains": ["Incidents", "ISPS"],
    "auto_include_severity": "low"
 }'::jsonb,
 'shield', '#455A64', 6),

('medical', 'Medical',
 'Medical facilities, crew health, and emergency medical response',
 ARRAY['Medical Supplies', 'Crew Health', 'First Aid', 'Medical Equipment', 'Certifications'],
 '{
    "sections": ["Medical Status", "Crew Health Issues", "Medical Inventory", "Certification Expiry"],
    "critical_domains": ["Crew Health", "Medical Supplies"],
    "auto_include_severity": "low"
 }'::jsonb,
 'heart', '#E91E63', 7),

('admin', 'Administration',
 'Financial management, HR, procurement, and regulatory compliance',
 ARRAY['Finance', 'HR', 'Procurement', 'Compliance', 'Insurance', 'Certifications', 'Port Formalities'],
 '{
    "sections": ["Financial Overview", "Crew Admin", "Procurement Status", "Compliance Items", "Certification Expiry"],
    "critical_domains": ["Compliance", "Certifications"],
    "auto_include_severity": "medium"
 }'::jsonb,
 'briefcase', '#607D8B', 8)

ON CONFLICT (id) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    owned_domains = EXCLUDED.owned_domains,
    handover_bucket_template = EXCLUDED.handover_bucket_template,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    display_order = EXCLUDED.display_order;


-- ============================================================================
-- RLS POLICIES: Master DB tables are read-only for authenticated users
-- ============================================================================

ALTER TABLE public.role_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.department_definitions ENABLE ROW LEVEL SECURITY;

-- Read-only policies for authenticated users
CREATE POLICY "role_definitions_read" ON public.role_definitions
    FOR SELECT TO authenticated
    USING (active = TRUE);

CREATE POLICY "department_definitions_read" ON public.department_definitions
    FOR SELECT TO authenticated
    USING (active = TRUE);

-- Service role can do everything
CREATE POLICY "role_definitions_service" ON public.role_definitions
    FOR ALL TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

CREATE POLICY "department_definitions_service" ON public.department_definitions
    FOR ALL TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);


-- ============================================================================
-- HELPER FUNCTIONS: Master DB utility functions
-- ============================================================================

-- Get all roles in a department
CREATE OR REPLACE FUNCTION public.get_roles_by_department(p_department TEXT)
RETURNS TABLE (
    id TEXT,
    display_name TEXT,
    abbreviation TEXT,
    rank_order INTEGER,
    authority_level TEXT
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
AS $$
    SELECT
        r.id,
        r.display_name,
        r.abbreviation,
        r.rank_order,
        r.authority_level
    FROM public.role_definitions r
    WHERE r.department = p_department
    AND r.active = TRUE
    ORDER BY r.rank_order ASC;
$$;

-- Get reporting chain for a role
CREATE OR REPLACE FUNCTION public.get_role_reporting_chain(p_role_id TEXT)
RETURNS TABLE (
    id TEXT,
    display_name TEXT,
    level INTEGER
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
AS $$
    WITH RECURSIVE chain AS (
        SELECT id, display_name, reports_to, 0 as level
        FROM public.role_definitions
        WHERE id = p_role_id

        UNION ALL

        SELECT r.id, r.display_name, r.reports_to, c.level + 1
        FROM public.role_definitions r
        INNER JOIN chain c ON r.id = c.reports_to
        WHERE c.reports_to IS NOT NULL
    )
    SELECT id, display_name, level
    FROM chain
    ORDER BY level ASC;
$$;

-- Get department with its roles
CREATE OR REPLACE FUNCTION public.get_department_with_roles(p_department_id TEXT)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'department', jsonb_build_object(
            'id', d.id,
            'display_name', d.display_name,
            'description', d.description,
            'owned_domains', d.owned_domains,
            'handover_bucket_template', d.handover_bucket_template,
            'icon', d.icon,
            'color', d.color
        ),
        'roles', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'id', r.id,
                    'display_name', r.display_name,
                    'abbreviation', r.abbreviation,
                    'rank_order', r.rank_order,
                    'authority_level', r.authority_level,
                    'reports_to', r.reports_to
                ) ORDER BY r.rank_order
            ), '[]'::jsonb)
            FROM public.role_definitions r
            WHERE r.department = p_department_id
            AND r.active = TRUE
        )
    )
    INTO v_result
    FROM public.department_definitions d
    WHERE d.id = p_department_id
    AND d.active = TRUE;

    RETURN COALESCE(v_result, '{}'::jsonb);
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_roles_by_department TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_role_reporting_chain TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_department_with_roles TO authenticated;


-- ============================================================================
-- VERIFICATION QUERIES (commented out for production)
-- ============================================================================

-- SELECT COUNT(*) as total_roles FROM public.role_definitions;
-- SELECT department, COUNT(*) as count FROM public.role_definitions GROUP BY department ORDER BY count DESC;
-- SELECT * FROM public.get_department_with_roles('engineering');
-- SELECT * FROM public.get_role_reporting_chain('deckhand');
