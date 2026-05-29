import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';

interface LoginRequest {
  username: string;
  password: string;
}

interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
}

interface MeResponse {
  username: string;
  is_admin: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'https://demokratyczny-backend.azurewebsites.net/api/auth';
  private currentUserSubject = new BehaviorSubject<string | null>(this.getStoredUsername());
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {}

  register(username: string, email: string, password: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/register`, {
      username,
      email,
      password
    });
  }

  login(username: string, password: string): Observable<AuthResponse> {
    const body = { username, password };
    const headers = new HttpHeaders({ 'Content-Type': 'application/json' });

  
    return this.http.post<AuthResponse>('https://demokratyczny-backend.azurewebsites.net/api/auth/login', body, { headers }).pipe(
      tap(response => {
        localStorage.setItem('token', response.access_token);
        localStorage.setItem('username', username);
        localStorage.setItem('is_admin', 'false');
        this.currentUserSubject.next(username);
      })
    );
  }

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('is_admin');
    this.currentUserSubject.next(null);
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('token');
  }

  whoAmI(): Observable<MeResponse> {
    return this.http.get<MeResponse>(`${this.apiUrl}/me`).pipe(
      tap(me => {
        localStorage.setItem('username', me.username);
        localStorage.setItem('is_admin', String(me.is_admin));
        this.currentUserSubject.next(me.username);
      })
    );
  }

  isAdmin(): boolean {
    return localStorage.getItem('is_admin') === 'true';
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  getCurrentUsername(): string | null {
    return localStorage.getItem('username');
  }

  private getStoredUsername(): string | null {
    return localStorage.getItem('username');
  }
}
