import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TemplateService, CreateTemplateRequest, Template } from '../../../core/services/template.service';
import { AuthService } from '../../../core/services/auth.service';

interface OptionItem {
  text: string;
  image_filename: string | null;
  uploading: boolean;
  uploadError: string | null;
}

@Component({
  selector: 'app-create-option-set',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './create-option-set.component.html',
  styleUrl: './create-option-set.component.css'
})
export class CreateOptionSetComponent implements OnInit {
  optionSet = {
    title: '',
    description: '',
    can_be_public: false,
  };

  options: OptionItem[] = [{ text: '', image_filename: null, uploading: false, uploadError: null }];

  isLoading = false;
  isEditing = false;
  editingId: number | null = null;
  isSavingCanBePublic = false;

  constructor(
    private templateService: TemplateService,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private http: HttpClient
  ) {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
    }
  }

  trackByIndex(index: number): number {
    return index;
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditing = true;
      this.editingId = +id;
      this.loadTemplateForEditing(+id);
    }
  }

  loadTemplateForEditing(id: number): void {
    this.templateService.getTemplate(id).subscribe({
      next: (template: Template) => {
        this.optionSet = {
          title: template.title,
          description: template.description || '',
          can_be_public: template.can_be_public,
        };
        this.options = template.options.map(opt => ({
          text: opt.text,
          image_filename: (opt as any).image_filename || null,
          uploading: false,
          uploadError: null
        }));
      },
      error: () => this.router.navigate(['/profile'])
    });
  }

  addOption(): void {
    this.options.push({ text: '', image_filename: null, uploading: false, uploadError: null });
  }

  removeOption(index: number): void {
    if (this.options.length > 1) {
      this.deleteImage(this.options[index].image_filename);
      this.options.splice(index, 1);
    }
  }

  onFileSelected(event: Event, index: number): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    this.deleteImage(this.options[index].image_filename);

    this.options[index].uploading = true;
    this.options[index].uploadError = null;

    const formData = new FormData();
    formData.append('file', file, file.name);

    this.http.post<any>('http://localhost:8000/api/upload/', formData).subscribe({
      next: (response) => {
        this.options[index].image_filename = response.filename;
        this.options[index].uploading = false;
      },
      error: (err) => {
        this.options[index].uploadError = err?.error?.detail || 'Upload nie powiódł się';
        this.options[index].uploading = false;
      }
    });
  }

  getImageUrl(filename: string | null): string | null {
    return filename ? `http://localhost:8000/api/upload/${filename}` : null;
  }

  deleteImage(filename: string | null): void {
    if (!filename) return;
    this.http.delete(`http://localhost:8000/api/upload/${filename}`).subscribe();
  }

  onCanBePublicChange(nextValue: boolean): void {
    this.optionSet.can_be_public = nextValue;

    if (!this.isEditing || !this.editingId || this.isSavingCanBePublic) return;

    this.isSavingCanBePublic = true;
    this.templateService.updateTemplateCanBePublic(this.editingId, this.optionSet.can_be_public).subscribe({
      next: (template) => {
        this.optionSet.can_be_public = template.can_be_public;
        this.isSavingCanBePublic = false;
      },
      error: () => {
        this.optionSet.can_be_public = !this.optionSet.can_be_public;
        this.isSavingCanBePublic = false;
      }
    });
  }

  onSubmit(): void {
    if (!this.optionSet.title.trim()) return;

    const validOptions = this.options.filter(o => o.text.trim() !== '');
    if (validOptions.length === 0) return;

    this.isLoading = true;

    const request: CreateTemplateRequest = {
      title: this.optionSet.title.trim(),
      description: this.optionSet.description?.trim() || undefined,
      can_be_public: this.optionSet.can_be_public,
      options: validOptions.map(o => o.text)
    };

    const operation = this.isEditing && this.editingId
      ? this.templateService.updateTemplate(this.editingId, request)
      : this.templateService.createTemplate(request);

    operation.subscribe({
      next: (savedTemplate) => {
        if (this.isEditing || savedTemplate) {
          const requests = savedTemplate.options
            .map((opt, i) => {
              const filename = validOptions[i]?.image_filename;
              if (filename && opt.id) {
                return this.http.patch(
                  `http://localhost:8000/api/templates/${savedTemplate.id}/options/${opt.id}/image?filename=${filename}`,
                  {}
                );
              }
              return null;
            })
            .filter(r => r !== null);

          if (requests.length > 0) {
            let done = 0;
            requests.forEach(r => r!.subscribe({
              next: () => { if (++done === requests.length) this.router.navigate(['/profile']); },
              error: () => { if (++done === requests.length) this.router.navigate(['/profile']); }
            }));
          } else {
            this.router.navigate(['/profile']);
          }
        }
      },
      error: () => { this.isLoading = false; }
    });
  }

  goBack(): void {
    this.router.navigate(['/profile']);
  }
}