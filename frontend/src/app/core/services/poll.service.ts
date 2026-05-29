import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PollService {
  private apiUrl = 'https://demokratyczny-backend.azurewebsites.net/api/polls';

  constructor(private http: HttpClient) {}

  getPolls(): Observable<any> {
    return this.http.get<any>(this.apiUrl);
  }

  getPoll(id: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/${id}`);
  }

  createPoll(poll: any): Observable<any> {
    return this.http.post<any>(this.apiUrl, poll);
  }

  vote(pollId: number, optionId: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${pollId}/vote`, { option_id: optionId });
  }
}
