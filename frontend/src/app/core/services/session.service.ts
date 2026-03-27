import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SessionCreateResponse {
  code: string;
  host: string;
}

export interface SessionStatusResponse {
  code: string;
  host: string;
  status: 'Host' | 'Participant';
}

@Injectable({
  providedIn: 'root'
})
export class SessionService {
  private apiUrl = 'http://localhost:8000/api/session';

  constructor(private http: HttpClient) {}

  createSession(): Observable<SessionCreateResponse> {
    return this.http.post<SessionCreateResponse>(`${this.apiUrl}/create`, {});
  }

  joinSession(code: string): Observable<SessionStatusResponse> {
    return this.http.post<SessionStatusResponse>(`${this.apiUrl}/${code}/join`, {});
  }

  getSession(code: string): Observable<SessionStatusResponse> {
    return this.http.get<SessionStatusResponse>(`${this.apiUrl}/${code}`);
  }

  leaveSession(code: string): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/${code}/leave`, {});
  }

  endSession(code: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${code}`);
  }
}
