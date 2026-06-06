import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TemplateOption {
  id: number;
  text: string;
  image_path?: string | null;
}

export interface TemplateOptionInput {
  text: string;
  image_path?: string | null;
}

export interface Template {
  id: number;
  title: string;
  description?: string;
  can_be_public: boolean;
  is_publish?: boolean;
  created_by: number;
  creator_username?: string;
  options: TemplateOption[];
}

export interface CreateTemplateRequest {
  title: string;
  description?: string;
  can_be_public: boolean;
  options: TemplateOptionInput[];
}

@Injectable({
  providedIn: 'root'
})
/** Service for template management including create, update, publish, and list operations. */
export class TemplateService {
  private apiUrl = 'https://demokratyczny-backend.azurewebsites.net/api/templates';

  constructor(private http: HttpClient) {}

  /**
   * Request a list of templates, optionally filtered by ownership.
   *
   * @param filter Optional filter string, such as 'mine'.
   * @returns An observable with the list of template objects.
   */
  getTemplates(filter?: string): Observable<Template[]> {
    const options = filter ? { params: { filter } } : {};
    return this.http.get<Template[]>(this.apiUrl, options);
  }

  /**
   * Retrieve a single template by its ID.
   *
   * @param id The template identifier.
   * @returns An observable with the requested template.
   */
  getTemplate(id: number): Observable<Template> {
    return this.http.get<Template>(`${this.apiUrl}/${id}`);
  }

  /**
   * Create a new template.
   *
   * @param template The payload for the new template.
   * @returns An observable with the created template.
   */
  createTemplate(template: CreateTemplateRequest): Observable<Template> {
    return this.http.post<Template>(this.apiUrl, template);
  }

  /**
   * Update an existing template.
   *
   * @param id The template identifier.
   * @param template The updated template payload.
   * @returns An observable with the updated template.
   */
  updateTemplate(id: number, template: CreateTemplateRequest): Observable<Template> {
    return this.http.put<Template>(`${this.apiUrl}/${id}`, template);
  }

  /**
   * Change a template's public visibility flag.
   *
   * @param id The template identifier.
   * @param canBePublic True to make the template public, false otherwise.
   * @returns An observable with the updated template.
   */
  updateTemplateCanBePublic(id: number, canBePublic: boolean): Observable<Template> {
    return this.http.patch<Template>(`${this.apiUrl}/${id}/can-be-public`, null, {
      params: { can_be_public: String(canBePublic) }
    });
  }

  /**
   * Delete a template by ID.
   *
   * @param id The template identifier to delete.
   * @returns An observable that completes when deletion is done.
   */
  deleteTemplate(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  /**
   * Publish a template through admin review.
   *
   * @param id The template identifier to publish.
   * @returns An observable with the publish result message.
   */
  publishTemplate(id: number): Observable<{id: number; message: string}> {
    return this.http.post<{id: number; message: string}>(`${this.apiUrl}/${id}/publish`, {});
  }

  /**
   * Retrieve templates available for admin review.
   *
   * @returns An observable with the list of reviewable templates.
   */
  getAdminReviewTemplates(): Observable<Template[]> {
    return this.http.get<Template[]>(`${this.apiUrl}/admin/review`);
  }

  /**
   * Retrieve a specific template pending admin review.
   *
   * @param id The template identifier.
   * @returns An observable with the requested template review details.
   */
  getAdminReviewTemplate(id: number): Observable<Template> {
    return this.http.get<Template>(`${this.apiUrl}/admin/review/${id}`);
  }

  /**
   * Retrieve publicly available templates.
   *
   * @returns An observable with a list of public templates.
   */
  getPublicTemplates(): Observable<Template[]> {
    return this.http.get<Template[]>(`${this.apiUrl}/public`);
  }

  /**
   * Publish a template from the admin review queue.
   *
   * @param id The template identifier to publish.
   * @returns An observable with the publish result.
   */
  publishFromAdminReview(id: number): Observable<{id: number; message: string}> {
    return this.http.post<{id: number; message: string}>(`${this.apiUrl}/admin/review/${id}/publish`, {});
  }

  rejectFromAdminReview(id: number): Observable<{message: string}> {
    return this.http.post<{message: string}>(`${this.apiUrl}/admin/review/${id}/reject`, {});
  }
}