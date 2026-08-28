/**
 * Frontend ↔ backend contract binding (issue #778, audit Q2).
 *
 * The `Api*` aliases are consumed straight from the generated OpenAPI types in
 * `@correlcore/api-types` (produced by `backend/scripts/export_openapi.py` +
 * `openapi-typescript`). New frontend code can import these instead of
 * re-declaring shapes.
 *
 * The `Assert<…>` block is a compile-time drift guard for the critical auth /
 * entries / insights DTOs. For each curated field the indexed access into the
 * generated schema fails to compile if the backend renames or removes the
 * field, and the direction-aware check fails on an incompatible re-type:
 *   - response fields use `Handles<Gen, Hand>` — every value the backend can
 *     send must fit the frontend type (so a new backend enum member the UI
 *     does not handle is caught);
 *   - request fields use `Sends<Hand, Gen>` — the value the frontend sends must
 *     be accepted by the backend field.
 * Optional/nullable representation is normalised away (`NonNullable`) because
 * the committed `packages/api-types/openapi.json` diff in CI already pins the
 * exact shape. Together they replace the enum-only `apiContract` test.
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

// entries — EntryResponse (response)
type _er_id = Assert<Handles<Entry['id'], EntryResponse['id']>>;
type _er_mood = Assert<Handles<Entry['mood_score'], EntryResponse['mood_score']>>;
type _er_energy = Assert<Handles<Entry['energy'], EntryResponse['energy']>>;
type _er_stress = Assert<Handles<Entry['stress'], EntryResponse['stress']>>;
type _er_date = Assert<Handles<Entry['entry_date'], EntryResponse['entry_date']>>;
type _er_slot = Assert<Handles<Entry['slot'], EntryResponse['slot']>>;
type _er_source = Assert<Handles<Entry['source'], EntryResponse['source']>>;
type _er_work = Assert<Handles<Entry['work_context'], EntryResponse['work_context']>>;

// entries — EntryCreate (request)
type _ec_date = Assert<Sends<EntryCreatePayload['entry_date'], EntryCreate['entry_date']>>;
type _ec_mood = Assert<Sends<EntryCreatePayload['mood_score'], EntryCreate['mood_score']>>;
type _ec_energy = Assert<Sends<EntryCreatePayload['energy'], EntryCreate['energy']>>;
type _ec_work = Assert<Sends<EntryCreatePayload['work_context'], EntryCreate['work_context']>>;

// auth — UserResponse (response)
type _ur_id = Assert<Handles<User['id'], UserResponse['id']>>;
type _ur_email = Assert<Handles<User['email'], UserResponse['email']>>;
type _ur_verified = Assert<Handles<User['is_verified'], UserResponse['is_verified']>>;
type _ur_admin = Assert<Handles<User['is_admin'], UserResponse['is_admin']>>;
type _ur_name = Assert<Handles<User['display_name'], UserResponse['display_name']>>;

// auth — TokenResponse (response)
type _tr_access = Assert<Handles<Token['access_token'], TokenResponse['access_token']>>;
type _tr_type = Assert<Handles<Token['token_type'], TokenResponse['token_type']>>;
type _tr_expires = Assert<Handles<Token['expires_in'], TokenResponse['expires_in']>>;

// auth — LoginRequest / RegisterRequest (request)
type _lr_email = Assert<Sends<LoginPayload['email'], Login['email']>>;
type _lr_pw = Assert<Sends<LoginPayload['password'], Login['password']>>;
type _rr_email = Assert<Sends<RegisterPayload['email'], Register['email']>>;
type _rr_pw = Assert<Sends<RegisterPayload['password'], Register['password']>>;

// insights — InsightResponse (response)
type _ir_id = Assert<Handles<Insight['id'], InsightResponse['id']>>;
type _ir_type = Assert<Handles<Insight['insight_type'], InsightResponse['insight_type']>>;
type _ir_tier = Assert<Handles<Insight['tier'], InsightResponse['tier']>>;
type _ir_metric = Assert<Handles<Insight['metric'], InsightResponse['metric']>>;
type _ir_n = Assert<Handles<Insight['sample_n'], InsightResponse['sample_n']>>;
type _ir_effect = Assert<Handles<Insight['effect_size'], InsightResponse['effect_size']>>;
type _ir_conf = Assert<Handles<Insight['confidence'], InsightResponse['confidence']>>;
