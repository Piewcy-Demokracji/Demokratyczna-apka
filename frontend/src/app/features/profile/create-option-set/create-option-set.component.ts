import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { TemplateService, CreateTemplateRequest, Template, TemplateOptionInput } from '../../../core/services/template.service';
import { AuthService } from '../../../core/services/auth.service';
import { UploadService } from '../../../core/services/upload.service';

interface OptionDraft {
  text: string;
  image_path: string | null;
  uploading?: boolean;
}

@Component({
  selector: 'app-create-option-set',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './create-option-set.component.html',
  styleUrl: './create-option-set.component.css'
})
export class CreateOptionSetComponent implements OnInit, OnDestroy {
  title = '';
  description = '';
  canBePublic = false;
  options: OptionDraft[] = [{ text: '', image_path: null }];

  isLoading = false;
  isEditing = false;
  editingId: number | null = null;
  isSavingCanBePublic = false;
  uploadError: string | null = null;

  // Paths loaded from DB on edit; treated as durable and never auto-deleted on cancel
  private originalPaths = new Set<string>();
  private submitted = false;

  constructor(
    private templateService: TemplateService,
    private authService: AuthService,
    private uploadService: UploadService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
    }
  }

  trackByIndex(index: number, item: any): number {
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

  ngOnDestroy(): void {
    window.removeEventListener('beforeunload', this.beforeUnloadHandler);
    if (this.submitted || this.isUnloading) {
    if (this.submitted) {
      return;
    }
    this.getOrphanedPaths().forEach(path =>
      this.uploadService.deleteImage(path).subscribe({ error: () => {} })
    );
  }

  private getOrphanedPaths(): string[] {
    return this.options
      .filter(opt => opt.image_path && !this.originalPaths.has(opt.image_path))
      .map(opt => opt.image_path as string);
  }

  loadTemplateForEditing(id: number): void {
    this.templateService.getTemplate(id).subscribe({
      next: (template: Template) => {
        this.title = template.title;
        this.description = template.description || '';
        this.canBePublic = template.can_be_public;
        this.options = template.options.length > 0
          ? template.options.map(opt => ({
              text: opt.text,
              image_path: opt.image_path ?? null
            }))
          : [{ text: '', image_path: null }];

        this.originalPaths = new Set(
          template.options
            .map(opt => opt.image_path)
            .filter((p): p is string => !!p)
        );
      },
      error: (error) => {
        console.error('Error loading template for editing:', error);
        this.router.navigate(['/profile']);
      }
    });
  }

  addOption(): void {
    this.options.push({ text: '', image_path: null });
  }

  removeOption(index: number): void {
    if (this.options.length <= 1) {
      return;
    }
    const path = this.options[index].image_path;
    if (path && !this.originalPaths.has(path)) {
      this.uploadService.deleteImage(path).subscribe({ error: () => {} });
    }
    this.options.splice(index, 1);
  }

  getImageUrl(path: string | null): string | null {
    return this.uploadService.getImageUrl(path);
  }

  onImageSelected(event: Event, index: number): void {
    this.uploadError = null;
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) {
      return;
    }
    const file = input.files[0];
    const validationError = this.uploadService.validateFile(file);
    if (validationError) {
      this.uploadError = validationError;
      input.value = '';
      return;
    }

    this.options[index].uploading = true;
    this.uploadService.uploadImage(file).subscribe({
      next: (response: { image_path: string }) => {
        this.options[index].image_path = response.image_path;
        this.options[index].uploading = false;
        input.value = '';
      },
      error: (err: unknown) => {
        console.error('Error uploading image:', err);
        this.uploadError = 'Nie udało się wgrać obrazka.';
        this.options[index].uploading = false;
        input.value = '';
      }
    });
  }

  removeImage(index: number): void {
    const path = this.options[index].image_path;
    if (path && !this.originalPaths.has(path)) {
      this.uploadService.deleteImage(path).subscribe({ error: () => {} });
    }
    this.options[index].image_path = null;
  }

  onCanBePublicChange(nextValue: boolean): void {
    this.canBePublic = nextValue;

    if (!this.isEditing || !this.editingId || this.isSavingCanBePublic) {
      return;
    }

    this.isSavingCanBePublic = true;
    this.templateService.updateTemplateCanBePublic(this.editingId, this.canBePublic).subscribe({
      next: (template) => {
        this.canBePublic = template.can_be_public;
        this.isSavingCanBePublic = false;
      },
      error: (error) => {
        console.error('Error updating can_be_public:', error);
        this.canBePublic = !this.canBePublic;
        this.isSavingCanBePublic = false;
      }
    });
  }

  onSubmit(): void {
    if (!this.title.trim()) {
      return;
    }

    const validOptions: TemplateOptionInput[] = this.options
      .filter(opt => opt.text.trim() !== '')
      .map(opt => ({
        text: opt.text.trim(),
        image_path: opt.image_path
      }));

    if (validOptions.length === 0) {
      return;
    }

    this.isLoading = true;

    const request: CreateTemplateRequest = {
      title: this.title.trim(),
      description: this.description?.trim() || undefined,
      can_be_public: this.canBePublic,
      options: validOptions
    };

    const operation = this.isEditing && this.editingId
      ? this.templateService.updateTemplate(this.editingId, request)
      : this.templateService.createTemplate(request);

    operation.subscribe({
      next: () => {
        this.submitted = true;
        this.router.navigate(['/profile']);
      },
      error: (error) => {
        console.error('Error saving option set:', error);
        this.isLoading = false;
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/profile']);
  }
}