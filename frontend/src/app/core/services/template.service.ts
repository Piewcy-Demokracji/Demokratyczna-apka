import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TemplateOption {
  id: number;
  text: string;
}

export interface Template {
  id: number;
  title: string;
  description?: string;
  is_public: boolean;
  created_by: number;
  options: TemplateOption[];
}

export interface CreateTemplateRequest {
  title: string;
  description?: string;
  is_public: boolean;
  options: string[];
}

@Injectable({
  providedIn: 'root'
})
export class TemplateService {
  private apiUrl = 'http://localhost:8000/api/templates';

  constructor(private http: HttpClient) {}

  getTemplates(filter?: string): Observable<Template[]> {
    const options = filter ? { params: { filter } } : {};
    return this.http.get<Template[]>(this.apiUrl, options);
  }

  getTemplate(id: number): Observable<Template> {
    return this.http.get<Template>(`${this.apiUrl}/${id}`);
  }

  createTemplate(template: CreateTemplateRequest): Observable<Template> {
    return this.http.post<Template>(this.apiUrl, template);
  }

  updateTemplate(id: number, template: CreateTemplateRequest): Observable<Template> {
    return this.http.put<Template>(`${this.apiUrl}/${id}`, template);
  }

  deleteTemplate(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}