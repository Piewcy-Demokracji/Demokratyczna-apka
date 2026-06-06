import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SessionOptionInput {
  text: string;
  image_path?: string | null;
}

export interface SessionCreateRequest {
  template_id?: number;
  duration_seconds?: number;
  options?: SessionOptionInput[] | string[];
  voting_mode?: 'stars' | 'single';
}

export interface SessionCreateResponse {
  token: string;
  code: string;
  host: string;
}

export interface PollOption {
  id: number;
  name: string;
  rating_count: number;
  total_rating: number;
  user_rating?: number;
  image_path?: string | null;
}

export interface Poll {
  id: number;
  title: string;
  duration_seconds: number;
  start_time: number;
  voting_mode: 'stars' | 'single';
  options: PollOption[];
}

export interface SessionStatusResponse {
  token: string;
  host: string;
  status: 'Host' | 'Participant';
  session_status?: 'ACTIVE' | 'ENDED' | 'DELETED';
  poll?: Poll;
  code?: string;
  image_base64?: string | null;
}

@Injectable({
  providedIn: 'root'
})
/** Service for interacting with session-related API endpoints and polling workflows. */
export class SessionService {
  private apiUrl = 'https://demokratyczny-backend.azurewebsites.net/api/session';

  constructor(private http: HttpClient) {}

  /**
   * Create a new live voting session.
   *
   * @param request Optional session creation payload.
   * @returns An observable containing the created session token, code, and host.
   */
  createSession(request?: SessionCreateRequest): Observable<SessionCreateResponse> {
    return this.http.post<SessionCreateResponse>(`${this.apiUrl}/create`, request || {});
  }

  /**
   * Join an existing voting session using a session code.
   *
   * @param code The public code of the session to join.
   * @returns An observable with the joined session status.
   */
  joinSession(code: string): Observable<SessionStatusResponse> {
    return this.http.post<SessionStatusResponse>(`${this.apiUrl}/join`, { code });
  }

  /**
   * Retrieve the current session status by token.
   *
   * @param token The session token to fetch status for.
   * @returns An observable with session status and poll details.
   */
  getSession(token: string): Observable<SessionStatusResponse> {
    return this.http.get<SessionStatusResponse>(`${this.apiUrl}/${token}`);
  }

  /**
   * Submit a vote for a session option.
   *
   * @param token The session token.
   * @param optionId The ID of the selected option.
   * @param rating The rating value for the option.
   * @returns An observable for the vote operation.
   */
  vote(token: string, optionId: number, rating: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${token}/vote`, {
      option_id: optionId,
      rating
    });
  }

  /**
   * End the session poll early as the host.
   *
   * @param token The session token to end early.
   * @returns An observable with the updated session status.
   */
  endPollEarly(token: string): Observable<SessionStatusResponse> {
    return this.http.post<SessionStatusResponse>(`${this.apiUrl}/${token}/end-poll-early`, {});
  }

  /**
   * Leave a session as a participant.
   *
   * @param token The session token to leave.
   * @returns An observable that completes when the leave operation finishes.
   */
  leaveSession(token: string): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/${token}/leave`, {});
  }

  /**
   * End and delete a session.
   *
   * @param token The session token to delete.
   * @returns An observable that completes when the session is deleted.
   */
  endSession(token: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${token}`);
  }
}
