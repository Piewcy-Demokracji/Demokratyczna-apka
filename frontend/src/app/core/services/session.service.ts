import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SessionCreateRequest {
  template_id?: number;
  duration_seconds?: number;
  options?: string[];
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
  poll?: Poll;
  code?: string;
  image_base64?: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class SessionService {
  private apiUrl = 'http://localhost:8000/api/session';

  constructor(private http: HttpClient) {}

  createSession(request?: SessionCreateRequest): Observable<SessionCreateResponse> {
    return this.http.post<SessionCreateResponse>(`${this.apiUrl}/create`, request || {});
  }

  joinSession(code: string): Observable<SessionStatusResponse> {
    return this.http.post<SessionStatusResponse>(`${this.apiUrl}/join`, { code });
  }

  getSession(token: string): Observable<SessionStatusResponse> {
    return this.http.get<SessionStatusResponse>(`${this.apiUrl}/${token}`);
  }

  vote(token: string, optionId: number, rating: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${token}/vote`, {
      option_id: optionId,
      rating
    });
  }

  endPollEarly(token: string): Observable<SessionStatusResponse> {
    return this.http.post<SessionStatusResponse>(`${this.apiUrl}/${token}/end-poll-early`, {});
  }

  leaveSession(token: string): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/${token}/leave`, {});
  }

  endSession(token: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${token}`);
  }
}
