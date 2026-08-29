/**
 * Frontend ↔ backend contract binding (issue #778, audit Q2).
 *
 * Two complementary layers guard against silent FE/BE drift:
 *
 *  1. The committed `packages/api-types/openapi.json` snapshot, regenerated and
 *     diffed in CI (`ci-contract.yml`). This is the comprehensive layer — it
 *     pins every field of every schema, including nested objects, optionality
 *     and nullability.
 *  2. The `Assert<…>` block below — a fast, frontend-side signal that surfaces
 *     drift at `pnpm typecheck` time for the scalar/enum fields of the critical
 *     auth / entries / insights DTOs. For each covered field, the indexed
 *     access into the generated schema fails to compile on a rename/removal,
 *     and the direction-aware check fails on an incompatible re-type:
 *       - response fields use `Handles<Gen, Hand>` — every value the backend
 *         can send must fit the frontend type (a new backend enum member the UI
 *         does not handle is caught);
 *       - request fields use `Sends<Hand, Gen>` — the value the frontend sends
 *         must be accepted by the backend field.
 *     Nested object fields (note markers/signals, token `user`, insight
 *     `flags`/`payload`) are intentionally left to layer 1, and `NonNullable`
 *     normalisation means optional/nullable drift is caught by layer 1 too.
 *
 * These do NOT subsume the enum-array / metric-range checks in
 * `backend/tests/test_api_contract.py` ↔ `$lib/contracts/apiContract.ts`, which
 * remain the source for those specific values.
 *
 * The `Api*` aliases are consumed straight from the generated types in
 * `@correlcore/api-types`; new frontend code can import them instead of
 * re-declaring shapes.
 */

import type { Schemas } from '@correlcore/api-types';

import type { EntryResponse, EntryCreatePayload } from './entries';
import type { UserResponse, TokenResponse, RegisterPayload, LoginPayload } from './auth';
import type { InsightResponse } from './insights';

// --- Canonical generated aliases (consume these in new frontend code) -------

export type ApiEntryResponse = Schemas['EntryResponse'];
export type ApiEntryCreate = Schemas['EntryCreate'];
export type ApiUserResponse = Schemas['UserResponse'];
export type ApiTokenResponse = Schemas['TokenResponse'];
export type ApiInsightResponse = Schemas['InsightResponse'];
export type ApiInsightListResponse = Schemas['InsightListResponse'];

// --- Compile-time drift guard ----------------------------------------------

type Assert<T extends true> = T;

/** A backend value must fit the frontend type — response fields. */
type Handles<Gen, Hand> = [NonNullable<Gen>] extends [NonNullable<Hand>] ? true : false;

/** A frontend value must be accepted by the backend field — request fields. */
type Sends<Hand, Gen> = [NonNullable<Hand>] extends [NonNullable<Gen>] ? true : false;

type Entry = Schemas['EntryResponse'];
type EntryCreate = Schemas['EntryCreate'];
type User = Schemas['UserResponse'];
type Token = Schemas['TokenResponse'];
type Login = Schemas['LoginRequest'];
type Register = Schemas['RegisterRequest'];
type Insight = Schemas['InsightResponse'];

// entries — EntryResponse (response). Every scalar/enum field; the nested
// note_markers / note_signals arrays are covered by the openapi.json snapshot.
type _er_id = Assert<Handles<Entry['id'], EntryResponse['id']>>;
type _er_user = Assert<Handles<Entry['user_id'], EntryResponse['user_id']>>;
type _er_date = Assert<Handles<Entry['entry_date'], EntryResponse['entry_date']>>;
type _er_slot = Assert<Handles<Entry['slot'], EntryResponse['slot']>>;
type _er_mood = Assert<Handles<Entry['mood_score'], EntryResponse['mood_score']>>;
type _er_energy = Assert<Handles<Entry['energy'], EntryResponse['energy']>>;
type _er_stress = Assert<Handles<Entry['stress'], EntryResponse['stress']>>;
type _er_cycle = Assert<Handles<Entry['cycle_day'], EntryResponse['cycle_day']>>;
type _er_bleed = Assert<
  Handles<Entry['cycle_bleeding_level'], EntryResponse['cycle_bleeding_level']>
>;
type _er_sleepm = Assert<Handles<Entry['sleep_minutes'], EntryResponse['sleep_minutes']>>;
type _er_sleepq = Assert<Handles<Entry['sleep_quality'], EntryResponse['sleep_quality']>>;
type _er_source = Assert<Handles<Entry['source'], EntryResponse['source']>>;
type _er_work = Assert<Handles<Entry['work_context'], EntryResponse['work_context']>>;
type _er_note = Assert<Handles<Entry['note'], EntryResponse['note']>>;
type _er_noteraw = Assert<Handles<Entry['note_raw'], EntryResponse['note_raw']>>;
type _er_notesum = Assert<
  Handles<Entry['note_summary_short'], EntryResponse['note_summary_short']>
>;
type _er_notevis = Assert<Handles<Entry['note_visibility'], EntryResponse['note_visibility']>>;
type _er_noteupd = Assert<Handles<Entry['note_updated_at'], EntryResponse['note_updated_at']>>;
type _er_created = Assert<Handles<Entry['created_at'], EntryResponse['created_at']>>;
type _er_updated = Assert<Handles<Entry['updated_at'], EntryResponse['updated_at']>>;

// entries — EntryCreate (request). Every hand field except `note_raw`, which the
// backend accepts only as a validation alias of `note` (aliases are not schema
// fields, so they never appear in the generated types).
type _ec_date = Assert<Sends<EntryCreatePayload['entry_date'], EntryCreate['entry_date']>>;
type _ec_slot = Assert<Sends<EntryCreatePayload['slot'], EntryCreate['slot']>>;
type _ec_mood = Assert<Sends<EntryCreatePayload['mood_score'], EntryCreate['mood_score']>>;
type _ec_energy = Assert<Sends<EntryCreatePayload['energy'], EntryCreate['energy']>>;
type _ec_stress = Assert<Sends<EntryCreatePayload['stress'], EntryCreate['stress']>>;
type _ec_cycle = Assert<Sends<EntryCreatePayload['cycle_day'], EntryCreate['cycle_day']>>;
type _ec_bleed = Assert<
  Sends<EntryCreatePayload['cycle_bleeding_level'], EntryCreate['cycle_bleeding_level']>
>;
type _ec_sleepm = Assert<Sends<EntryCreatePayload['sleep_minutes'], EntryCreate['sleep_minutes']>>;
type _ec_sleepq = Assert<Sends<EntryCreatePayload['sleep_quality'], EntryCreate['sleep_quality']>>;
type _ec_source = Assert<Sends<EntryCreatePayload['source'], EntryCreate['source']>>;
type _ec_work = Assert<Sends<EntryCreatePayload['work_context'], EntryCreate['work_context']>>;
type _ec_note = Assert<Sends<EntryCreatePayload['note'], EntryCreate['note']>>;
type _ec_notesum = Assert<
  Sends<EntryCreatePayload['note_summary_short'], EntryCreate['note_summary_short']>
>;
type _ec_notevis = Assert<
  Sends<EntryCreatePayload['note_visibility'], EntryCreate['note_visibility']>
>;

// auth — UserResponse (response)
type _ur_id = Assert<Handles<User['id'], UserResponse['id']>>;
type _ur_email = Assert<Handles<User['email'], UserResponse['email']>>;
type _ur_name = Assert<Handles<User['display_name'], UserResponse['display_name']>>;
type _ur_verified = Assert<Handles<User['is_verified'], UserResponse['is_verified']>>;
type _ur_admin = Assert<Handles<User['is_admin'], UserResponse['is_admin']>>;

// auth — TokenResponse (response). Nested `user` covered by the snapshot.
type _tr_access = Assert<Handles<Token['access_token'], TokenResponse['access_token']>>;
type _tr_refresh = Assert<Handles<Token['refresh_token'], TokenResponse['refresh_token']>>;
type _tr_type = Assert<Handles<Token['token_type'], TokenResponse['token_type']>>;
type _tr_expires = Assert<Handles<Token['expires_in'], TokenResponse['expires_in']>>;

// auth — LoginRequest / RegisterRequest (request)
type _lr_email = Assert<Sends<LoginPayload['email'], Login['email']>>;
type _lr_pw = Assert<Sends<LoginPayload['password'], Login['password']>>;
type _lr_remember = Assert<Sends<LoginPayload['remember_me'], Login['remember_me']>>;
type _rr_email = Assert<Sends<RegisterPayload['email'], Register['email']>>;
type _rr_pw = Assert<Sends<RegisterPayload['password'], Register['password']>>;
type _rr_name = Assert<Sends<RegisterPayload['display_name'], Register['display_name']>>;

// insights — InsightResponse (response). Nested `flags`/`payload` records are
// covered by the snapshot.
type _ir_id = Assert<Handles<Insight['id'], InsightResponse['id']>>;
type _ir_user = Assert<Handles<Insight['user_id'], InsightResponse['user_id']>>;
type _ir_type = Assert<Handles<Insight['insight_type'], InsightResponse['insight_type']>>;
type _ir_tier = Assert<Handles<Insight['tier'], InsightResponse['tier']>>;
type _ir_metric = Assert<Handles<Insight['metric'], InsightResponse['metric']>>;
type _ir_subtype = Assert<Handles<Insight['subject_type'], InsightResponse['subject_type']>>;
type _ir_subid = Assert<Handles<Insight['subject_id'], InsightResponse['subject_id']>>;
type _ir_sublabel = Assert<Handles<Insight['subject_label'], InsightResponse['subject_label']>>;
type _ir_effect = Assert<Handles<Insight['effect_size'], InsightResponse['effect_size']>>;
type _ir_conf = Assert<Handles<Insight['confidence'], InsightResponse['confidence']>>;
type _ir_n = Assert<Handles<Insight['sample_n'], InsightResponse['sample_n']>>;
type _ir_stmt = Assert<Handles<Insight['statement'], InsightResponse['statement']>>;
type _ir_fordate = Assert<
  Handles<Insight['generated_for_date'], InsightResponse['generated_for_date']>
>;
type _ir_genat = Assert<Handles<Insight['generated_at'], InsightResponse['generated_at']>>;
type _ir_created = Assert<Handles<Insight['created_at'], InsightResponse['created_at']>>;
type _ir_updated = Assert<Handles<Insight['updated_at'], InsightResponse['updated_at']>>;
